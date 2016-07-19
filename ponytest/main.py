
import sys
from unittest import suite, TestProgram as _TestProgram, SkipTest
from unittest.loader import TestLoader as _TestLoader

from functools import wraps
from itertools import product
from collections import deque, Iterable

from .utils import PY2, ContextManager, ValidationError
if not PY2:
    from contextlib import contextmanager, ExitStack, ContextDecorator
else:
    from contextlib2 import contextmanager, ExitStack, ContextDecorator

import types
import unittest


from collections import OrderedDict
from copy import copy

class FixturesRegistry(OrderedDict):

    def __init__(self, *args, **kwargs):
        self.providers = kwargs.pop('providers', {})
        super(FixturesRegistry, self).__init__(*args, **kwargs)

    def provider(self):
        def decorator(obj):
            fixture = obj.KEY
            provider = getattr(obj, 'PROVIDER', None)
            if provider is None:
                provider = getattr(obj, '__name__', None)
            self.providers.setdefault(fixture, {}) \
                [provider] = obj
            return obj
        return decorator

    def __copy__(self):
        return self.__class__(self, providers=self.providers)

    def merge(self, obj, append_left=False):
        if isinstance(obj, dict):
            obj = obj.items()
        to_merge = self.__class__(providers=self.providers)
        for item in obj:
            if not isinstance(obj, tuple):
                obj = (obj, {})
            key, config = item
            to_merge[key] = config
        if append_left:
            ret = copy(self)
            ret.update(to_merge)
            return ret
        to_merge.update(self)
        return to_merge


def SetupTeardownFixture(setUpFunc, tearDownFunc):
    @contextmanager
    def fixture(test):
        try:
            setUpFunc(test)
            yield
        finally:
            tearDownFunc(test)
    fixture.weight = 20
    return fixture


def empty(test):
    pass


class TestLoader(_TestLoader):
    pony_fixtures = FixturesRegistry()

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
        elif isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            return self.loadTestsFromTestCase(obj)
        elif (callable(obj) and
              isinstance(parent, type) and
              issubclass(parent, unittest.TestCase)):
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



    def _sorted(self, fixtures):
        return sorted(fixtures, key=lambda f: getattr(f, 'weight', 0),
                      reverse=True)

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

    def _handle_excluded(self, fixtures, Test):
        excluded = getattr(Test, 'exclude_fixtures', ())
        if not isinstance(Test, type):
            method = getattr(Test, Test._testMethodName)
            excluded = getattr(method, 'exclude_fixtures', excluded)
        return [
            f for f in fixtures if getattr(f, 'KEY', NotImplemented) not in excluded
        ]

    def _make_suite(self, names, klass, fixtures):
        dic = {
            'fixtures': fixtures,
            'setUp': empty, 'tearDown': empty,
            'setUpClass': classmethod(empty), 'tearDownClass': classmethod(empty),
        }
        test_scoped = []
        class_scoped = []

        for F in fixtures:
            if self._is_test_scoped(F, klass):
                test_scoped.append(F)
            if self._is_class_scoped(F, klass):
                class_scoped.append(F)

        _setUp = klass.setUp
        if PY2:
            _setUp = _setUp.__func__
        _tearDown = klass.tearDown
        if PY2:
            _tearDown = _tearDown.__func__

        test_scoped.append(
            SetupTeardownFixture(_setUp, _tearDown)
        )

        _setUpClass = klass.setUpClass.__func__
        _tearDownClass = klass.tearDownClass.__func__
        class_scoped.append(
            SetupTeardownFixture(_setUpClass, _tearDownClass)
        )

        for name in names:
            func = getattr(klass, name)
            if PY2:
                func = func.__func__
            @wraps(func)
            def wrapper(test, _test_func=func):
                fixtures = self._handle_excluded(test_scoped, test)
                for F in self._sorted(fixtures):
                    transform = F(test)
                    _test_func = transform(_test_func)
                _test_func(test, )

            dic[name] = wrapper

        def case(cls, result):
            cls._result = result
            def func(cls):
                s = self.suiteClass(
                    [cls(name) for name in names]
                )
                s(result)
            fixtures = self._handle_excluded(class_scoped, cls)
            for F in self._sorted(fixtures):
                wrapper = F(cls)
                func = wrapper(func)
            Case = type(cls.__name__, (unittest.TestCase,), {
                'case': lambda t: func(cls),
            })
            Case.__module__ = cls.__module__
            case = Case('case')
            case(result)

        dic['case'] = classmethod(case)

        fixture_names = tuple(
            f.fixture_name
            for f in fixtures if getattr(f, 'fixture_name', None)
        )
        type_name = klass.__name__
        if fixture_names:
           type_name  = '_'.join((type_name, 'with') + fixture_names)

        new_klass = type(type_name, (klass,), dic)
        new_klass.__module__ = klass.__module__

        return self.suiteClass([new_klass.case])

    def loadTestsFromTestCase(self, testCaseClass):
        assert not issubclass(testCaseClass, suite.TestSuite)
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        fixture_chains = list(self.iter_fixture_chains(testCaseClass))
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

    def iter_fixture_chains(self, klass):
        provider_sets = [l for l in self.iter_provider_sets(klass) if l]
        for fixture_chain in product(*provider_sets):
            try:
                fixture_chain = [
                    f for f in fixture_chain if f is not None
                    if not hasattr(f, 'validate') or f.validate(fixture_chain, klass)
                ]
            except ValidationError:
                continue
            yield fixture_chain

    def iter_provider_sets(self, klass):
        pony_fixtures = getattr(klass, 'pony_fixtures', self.pony_fixtures)
        for key, providers in pony_fixtures.items():
            if callable(providers):
                providers = providers()
            if providers is not None:
                yield [
                    p if callable(p) else pony_fixtures.providers[key][p]
                    for p in providers
                ]
                continue
            yield pony_fixtures.providers[key].values()



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

