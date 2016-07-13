
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

            fixture_chains = self.get_fixture_chains(parent)
            if not fixture_chains:
                return self.suiteClass([])

            suites = []
            for chain in fixture_chains:
                s = self._make_suite([name], parent, chain)
                suites.append(s)
            if not suites:
                return super(TestLoader, self).loadTestsFromName(
                    name, module
                )
            if len(suites) > 1:
                return self.suiteClass(suites)
            return suites[0]

    class SetupTeardownFixture(object):
        test = None
        weight = 100

        def __init__(self, setUpFunc, tearDownFunc):
            self.setUpFunc = setUpFunc
            self.tearDownFunc = tearDownFunc

        def __call__(self, test):
            self.test = test
            return self

        def __enter__(self):
            self.setUpFunc(self.test)

        def __exit__(self, *exc_info):
            self.tearDownFunc(self.test)

    def _sorted(self, fixtures):
        return sorted(fixtures, key=lambda f: getattr(f, 'weight', 0))


    def _is_test_scoped(self, fixture, klass):
        if hasattr(fixture, 'KEY'):
            if fixture.KEY in getattr(klass, 'test_scoped', ()):
                return True
            if fixture.KEY not in getattr(klass, 'test_scoped', ()) \
                    and  fixture.KEY in getattr(klass, 'class_scoped', ()):
                return False
        return not getattr(fixture, 'class_scoped', False)

    def _is_class_scoped(self, fixture, klass):
        if hasattr(fixture, 'KEY'):
            if fixture.KEY in getattr(klass, 'class_scoped', ()):
                return True
            if fixture.KEY not in getattr(klass, 'class_scoped', ()) \
                    and  fixture.KEY in getattr(klass, 'test_scoped', ()):
                return False
        return getattr(fixture, 'class_scoped', False)

    def _make_suite(self, names, klass, fixtures):
        dic = {
            'fixtures': fixtures,
        }
        if hasattr(klass, 'exclude_fixtures'):
            fixtures = [f for f in fixtures if getattr(f, 'KEY', NotImplemented) not in klass.exclude_fixtures]

        test_scoped = []
        for Ctx in fixtures:
            if self._is_test_scoped(Ctx, klass):
                test_scoped.append(Ctx)

        test_wrappers = []

        stacks = {name: ExitStack() for name in names}

        _setUp = klass.setUp
        if PY2:
            _setUp = _setUp.__func__
        _tearDown = klass.tearDown
        if PY2:
            _tearDown = _tearDown.__func__

        test_scoped.append(
            self.SetupTeardownFixture(_setUp, _tearDown)
        )

        def setUp(test):
            stack = stacks[test._testMethodName]
            with stack:
                for Ctx in self._sorted(test_scoped):
                    ctx = Ctx(test)

                    if isinstance(ctx, ContextManager):
                        stack.enter_context(ctx)
                    else:
                        assert callable(ctx)
                        test_wrappers.append(ctx)
                stacks[test._testMethodName] = stack.pop_all()
        dic['setUp'] = setUp


        def tearDown(test):
            stack = stacks[test._testMethodName]
            stack.close()
        dic['tearDown'] = tearDown

        for name in names:
            func = getattr(klass, name)
            if PY2:
                func = func.__func__
            @wraps(func)
            def wrapper(test, _test_func=func, *arg, **kw):
                stack = stacks[test._testMethodName]
                with stack:
                    for transform in self._sorted(test_wrappers):
                        _test_func = transform(_test_func)
                    _test_func(test, *arg, **kw)
                    stacks[test._testMethodName] = stack.pop_all()

            dic[name] = wrapper

        stack_holder = [ExitStack()]

        def setUpClass(cls, *arg, **kw):
            stack = stack_holder[0]
            with stack:
                for ctx in self._sorted(suite_contexts):
                    stack.enter_context(ctx)
                stack_holder[0] = stack.pop_all()
        dic['setUpClass'] = classmethod(setUpClass)


        def tearDownClass(cls, *arg, **kw):
            stack = stack_holder[0]
            stack.close()
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

        _setUpClass = klass.setUpClass.__func__
        _tearDownClass = klass.tearDownClass.__func__
        Fixture = self.SetupTeardownFixture(_setUpClass, _tearDownClass)
        suite_contexts = [
            Fixture(new_klass)
        ]
        suite_wrappers = []

        # do the same as with tests

        for Ctx in fixtures:
            if not self._is_class_scoped(Ctx, klass):
                continue
            ctx = Ctx(new_klass)
            if isinstance(ctx, ContextManager):
                suite_contexts.append(ctx)
            else:
                assert callable(ctx)
                suite_wrappers.append(ctx)

        s = self.suiteClass(
            [new_klass(name) for name in names]
        )
        # descriptor ?
        def suite(cls, *args):
            s = self.suiteClass(
                [cls(name) for name in names]
            )
            s(*args)

        for transform in self._sorted(suite_wrappers):
            suite = transform(suite)

        return self.suiteClass([new_klass.suite]) # s = classmethod

    def loadTestsFromTestCase(self, testCaseClass):
        assert not issubclass(testCaseClass, suite.TestSuite)
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        fixture_chains = self.get_fixture_chains(testCaseClass)
        if not fixture_chains:
            return self.suiteClass([])

        suites = []
        for chain in fixture_chains:
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
            fixture_chain = [f for f in fixture_chain if f is not None]
            for f in tuple(fixture_chain):
                if not hasattr(f, 'validate'):
                    continue
                fixture_chain = f.validate(fixture_chain, klass)
                if fixture_chain is None:
                    break
            else:
                ret.append(fixture_chain)
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

