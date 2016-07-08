
import sys
from unittest import suite, TestProgram as _TestProgram, SkipTest
from unittest.loader import TestLoader as _TestLoader

from functools import wraps
from itertools import product
from collections import deque, Iterable

from .utils import PY2, ContextManager
if not PY2:
    from contextlib import contextmanager, ExitStack
else:
    from contextlib2 import contextmanager, ExitStack

import types
from unittest import case

class TestLoader(_TestLoader):
    pony_fixtures = deque()

    def loadTestsFromName(self, name, module=None):
        parts = name.split('.')
        if module is None:
            parts_copy = parts[:]
            while parts_copy:
                try:
                    module = __import__('.'.join(parts_copy))
                    break
                except ImportError:
                    del parts_copy[-1]
                    if not parts_copy:
                        raise
            parts = parts[1:]
        obj = module
        for part in parts:
            parent, obj = obj, getattr(obj, part)

        if isinstance(obj, types.ModuleType):
            return self.loadTestsFromModule(obj)
        elif isinstance(obj, type) and issubclass(obj, case.TestCase):
            return self.loadTestsFromTestCase(obj)
        elif (callable(obj) and
              isinstance(parent, type) and
              issubclass(parent, case.TestCase)):
            name = parts[-1]

            suites = []
            for chain in self.get_fixture_chains(parent):
                s = self._make_suite([name], parent, chain)
                suites.append(s)
            if not suites:
                return super(TestLoader, self).loadTestsFromName(
                    name, module
                )
            if len(suites) > 1:
                return self.suiteClass(suites)
            return suites[0]

    def _make_suite(self, names, klass, fixtures):
        if not fixtures:
            return self.suiteClass(
                [klass(name) for name in names]
            )

        # wrappers = [f for f in fixtures if getattr(f, 'is_wrapper', False)]
        # fixtures = [f for f in fixtures if not f in wrappers]

        test_scoped = []
        for Ctx in fixtures:
            if not getattr(Ctx, 'class_scoped', False):
                test_scoped.append(Ctx)

        dic = {}

        test_wrappers = []

        if test_scoped:
            stacks = {name: ExitStack() for name in names}

            _setUp = klass.setUp
            if PY2:
                _setUp = _setUp.__func__
            @wraps(_setUp)
            def setUp(test):
                stack = stacks[test._testMethodName]
                try:
                    for Ctx in test_scoped:
                        Ctx(test)
                except SkipTest:
                    # FIXME impl better
                    raise

                with stack:
                    for Ctx in test_scoped:
                        ctx = Ctx(test)
                        if isinstance(ctx, ContextManager):
                            stack.enter_context(ctx)

                    # TODO maybe allow ctx managers that execute after test setUp?
                    _setUp(test)
                    stacks[test._testMethodName] = stack.pop_all()
            dic['setUp'] = setUp

            _tearDown = klass.tearDown
            if PY2:
                _tearDown = _tearDown.__func__
            @wraps(_tearDown)
            def tearDown(test):
                stack = stacks[test._testMethodName]
                with stack:
                    _tearDown(test)
            dic['tearDown'] = tearDown

            for name in names:
                func = getattr(klass, name)
                if PY2:
                    func = func.__func__
                @wraps(func)
                def wrapper(test, _test_func=func, *arg, **kw):
                    stack = stacks[test._testMethodName]
                    with stack:
                        _test_func(test, *arg, **kw)
                        stacks[test._testMethodName] = stack.pop_all()
                for transform in test_wrappers:
                    wrapper = transform(wrapper)
                dic[name] = wrapper

        class_scoped = [Ctx for Ctx in fixtures if Ctx not in test_scoped]
        suite_wrappers = []

        if class_scoped:
            stack_holder = [ExitStack()]

            _setUpClass = klass.setUpClass.__func__

            for Ctx in class_scoped:
                ctx = Ctx(klass)
                if not isinstance(ctx, ContextManager):
                    assert callable(ctx)
                    suite_wrappers.append(ctx)

            @wraps(_setUpClass)
            def setUpClass(cls, *arg, **kw):
                stack = stack_holder[0]
                try:
                    for Ctx in class_scoped:
                        Ctx(cls)
                except SkipTest:
                    # FIXME impl better
                    # TODO remove ?
                    raise

                with stack:
                    for Ctx in class_scoped:
                        ctx = Ctx(cls)
                        if isinstance(ctx, ContextManager):
                            stack.enter_context(ctx)
                    _setUpClass(cls, *arg, **kw)
                    stack_holder[0] = stack.pop_all()
            dic['setUpClass'] = classmethod(setUpClass)

            _tearDownClass = klass.tearDownClass.__func__
            @wraps(_tearDownClass)
            def tearDownClass(cls, *arg, **kw):
                stack = stack_holder[0]
                with stack:
                    return _tearDownClass(cls, *arg, **kw)
            dic['tearDownClass'] = classmethod(tearDownClass)

        fixture_names = tuple(
            f.fixture_name
            for f in fixtures if getattr(f, 'fixture_name', None)
        )
        type_name = klass.__name__
        if fixture_names:
           type_name  = '_'.join((type_name, 'with') + fixture_names)
        new_klass = type(type_name, (klass,), dic)
        new_klass.__module__ = klass.__module__
        s = self.suiteClass(
            [new_klass(name) for name in names]
        )
        if not suite_wrappers:
            return s
        for transform in suite_wrappers:
            s = transform(s)
        return self.suiteClass([s])

    # 1. TODO pass class to fixture's invoke method
    # fixtures to be accessible from class automatically (?)
    # 2. if is contextmanager


    def loadTestsFromTestCase(self, testCaseClass):
        assert not issubclass(testCaseClass, suite.TestSuite)
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        suites = []
        for chain in self.get_fixture_chains(testCaseClass):
            s = self._make_suite(testCaseNames, testCaseClass, chain)
            suites.append(s)
        if not suites:
            return super(TestLoader, self).loadTestsFromTestCase(testCaseClass)
        if len(suites) > 1:
            ret = self.suiteClass(suites)
        else:
            ret = suites[0]
        return ret

    def get_fixture_chains(self, klass):
        fixture_sets = []
        pony_fixtures = getattr(klass, 'pony_fixtures', self.pony_fixtures)
        for ctx in pony_fixtures:
            if not isinstance(ctx, Iterable):
                ctx = ctx()
            fixtures = tuple(ctx)
            if fixtures:
                fixture_sets.append(fixtures)
        ret = []
        for fixture_chain in product(*fixture_sets):
            ret.append(
                tuple(fixture_chain)
            )
        return ret


class TestProgram(_TestProgram):
    def __init__(self, *args, **kwargs):
        try:
            kwargs['argv'] = sys.argv[:sys.argv.index('--')]
            sys.argv.remove('--')
        except ValueError:
            pass
        kwargs['testLoader'] = TestLoader()
        super(TestProgram, self).__init__(*args, **kwargs)

pony_fixtures = TestLoader.pony_fixtures

