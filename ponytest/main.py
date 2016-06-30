
import sys
from unittest import suite, TestProgram as _TestProgram
from unittest.loader import TestLoader as _TestLoader

from functools import wraps
from itertools import product
from collections import deque, Iterable

from .utils import PY2
if not PY2:
    from contextlib import contextmanager, ExitStack
else:
    from contextlib2 import contextmanager, ExitStack


class TestLoader(_TestLoader):
    pony_fixtures = deque()

    def _make_tests(self, names, klass, fixtures):
        if not fixtures:
            return [klass(name) for name in names]
        test_scoped = []
        for Ctx in fixtures:
            if not getattr(Ctx, 'class_scoped', False):
                test_scoped.append(Ctx)

        dic = {}
        if test_scoped:
            stacks = {name: ExitStack() for name in names}

            _setUp = klass.setUp
            if PY2:
                _setUp = _setUp.__func__
            @wraps(_setUp)
            def setUp(test):
                stack = stacks[test._testMethodName]
                with stack:
                    for Ctx in test_scoped:
                        ctx = Ctx(test)
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
                if not test_scoped:
                    break
                func = getattr(klass, name)
                if PY2:
                    func = func.__func__
                @wraps(func)
                def wrapper(test, *arg, **kw):
                    stack = stacks[test._testMethodName]
                    with stack:
                        func(test, *arg, **kw)
                        stacks[test._testMethodName] = stack.pop_all()
                dic[name] = wrapper

        class_scoped = [Ctx for Ctx in fixtures if Ctx not in test_scoped]

        if class_scoped:
            stack_holder = [ExitStack()]

            _setUpClass = klass.setUpClass.__func__
            @wraps(_setUpClass)
            def setUpClass(cls, *arg, **kw):
                stack = stack_holder[0]
                with stack:
                    for Ctx in class_scoped:
                        ctx = Ctx(cls)
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
        type_name = '_'.join((klass.__name__, 'with') + fixture_names)
        new_klass = type(type_name, (klass,), dic)
        new_klass.__module__ = klass.__module__
        return [new_klass(name) for name in names]

    def loadTestsFromTestCase(self, testCaseClass):
        assert not issubclass(testCaseClass, suite.TestSuite)
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        suites = []
        for chain in self.get_fixture_chains(testCaseClass):
            tests = self._make_tests(testCaseNames, testCaseClass, chain)
            suites.append(
                self.suiteClass(tests)
            )
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

