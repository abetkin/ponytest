
from functools import wraps, partial
from itertools import product
from collections import deque, Iterable, Mapping

from .utils import PY2, ContextManager, ValidationError, add_metaclass, no_op, \
        merge_attrs, with_cli_args
import click
if not PY2:
    from contextlib import contextmanager, ExitStack, ContextDecorator
else:
    from contextlib2 import contextmanager, ExitStack, ContextDecorator

from .config import fixture_providers, fixture_handlers, pony_fixtures


import unittest

from .is_standalone import is_standalone_use



def provider(key=None, provider=None, **kwargs):
    def decorator(obj, key=key, provider=provider):
        if key is None:
            key = obj.KEY
        elif not hasattr(obj, 'KEY'):
            obj.KEY = key
        else:
            assert obj.KEY == key
        if provider is None:
            assert fixture_providers.get(key, {}).get('default', obj) is obj
            provider = 'default'

        elif not hasattr(obj, 'PROVIDER'):
            obj.PROVIDER = provider
        else:
            assert obj.PROVIDER == provider
        fixture_providers.setdefault(key, {}) \
            [provider] = obj
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj
    return decorator


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



class LazyFixture(object):
    def __init__(self, lazy_fixtures):
        self.fixtures = lazy_fixtures

    def __get__(self, Test, test):
        Test = Test or test

        def get_fixture(name):
            F = next(f for f in self.fixtures if f.KEY == name)
            fixture = F(Test)
            assert isinstance(fixture, ContextManager)
            return fixture

        return get_fixture


class Meta(type):

    def __new__(cls, name, bases, namespace):
        klass = super(Meta, cls).__new__(cls, name, bases, namespace)
        if namespace.get('disable_Meta'):
            return klass
        if not is_standalone_use():
            return klass
        names = unittest.loader.TestLoader().getTestCaseNames(klass)
        mgr = FixtureManager(klass, names, test_level_config=False)
        mgr = list(mgr)
        names, fixtures, config = mgr[0]
        # if not fixture_chains:
        #     return klass

        builder = ClassFixturesAreContextManagers(klass, fixtures, names, config)
        dic = builder.prepare_case()
        namespace.update(dic)
        return super(Meta, cls).__new__(cls, name, bases, namespace)

    def __init__(cls, name, bases, namespace):
        if namespace.get('disable_Meta'):
            return
        if not hasattr(cls, 'with_fixtures'):
            cls.with_fixtures = []

@add_metaclass(Meta)
class TestCase(unittest.TestCase):

    disable_Meta = True

    def __str__(self):
        return ' '.join([
            unittest.TestCase.__str__(self),
            '[%s]' % ', '.join(self.with_fixtures),
        ])


class CaseBuilder(object):

    def __init__(self, testcase_cls, fixtures, names, config):
        self.klass = testcase_cls
        try:
            fixtures['class'], fixtures['test'], fixtures['lazy']
        except:
            fixtures = self._group_by_scope(testcase_cls, fixtures, config)
        self.fixtures = fixtures
        self.names = names
        self.config = config

    @classmethod
    def factory(cls, testcase_cls, fixtures, names, config):
        scopes = cls._group_by_scope(testcase_cls, fixtures, config)
        for F in scopes['class']:
            if not isinstance(F(testcase_cls), ContextManager):
                builder = ClassFixturesCanBeCallables
                break
        else:
            builder = ClassFixturesAreContextManagers
        return builder(testcase_cls, scopes, names, config)

    def prepare_case(self):
        '''
        Prepare the namespace for the new testcase class.
        '''
        raise NotImplementedError

    def make_suite(self):
        '''
        Make a testsuite out of this testcase class.
        '''
        raise NotImplementedError

    @property
    def fixture_names(self):
        ret = []
        for scope in ['class', 'test']:
            for f in self.fixtures[scope]:
                if getattr(f, 'fixture_name', None):
                    ret.append(f.fixture_name)
        return ret

    @staticmethod
    def _sort(fixtures):
        return sorted(fixtures, key=lambda f: getattr(f, 'weight', 0))

    @staticmethod
    def _is_test_scoped(fixture, config):
        if hasattr(fixture, 'KEY'):
            if fixture.KEY in getattr(config, 'test_scoped', ()):
                return True
            if fixture.KEY not in getattr(config, 'test_scoped', ()) \
                    and  fixture.KEY in getattr(config, 'class_scoped', ()):
                return False
        return getattr(fixture, 'scope', 'test') == 'test'

    @staticmethod
    def _is_class_scoped(fixture, config):
        if hasattr(fixture, 'KEY'):
            if fixture.KEY in getattr(config, 'class_scoped', ()):
                return True
            if fixture.KEY not in getattr(config, 'class_scoped', ()) \
                    and  fixture.KEY in getattr(config, 'test_scoped', ()):
                return False
        return getattr(fixture, 'scope', 'test') == 'class'

    @staticmethod
    def _is_lazy(fixture, config):
        if hasattr(fixture, 'KEY'):
            if fixture.KEY in getattr(config, 'lazy_fixtures', ()):
                return True
        return getattr(fixture, 'scope', 'test') == 'lazy'

    @classmethod
    def _group_by_scope(cls, klass, fixtures, config):
        test_scoped = []
        class_scoped = []
        lazy_fixtures = []

        for F in fixtures:
            if cls._is_lazy(F, config):
                lazy_fixtures.append(F)
                continue
            if cls._is_test_scoped(F, config):
                test_scoped.append(F)
            if cls._is_class_scoped(F, config):
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
        return {
            'test': cls._sort(test_scoped),
            'class': cls._sort(class_scoped),
            'lazy': cls._sort(lazy_fixtures),
        }


class ClassFixturesAreContextManagers(CaseBuilder):

    def prepare_case(self):
        dic = {}

        for name in self.names:
            func = getattr(self.klass, name)
            if PY2:
                func = func.__func__
            @wraps(func)
            def wrapper(test, _test_func=func):
                fixtures = [F(test) for F in self.fixtures['test']]
                if not all(isinstance(f, ContextManager) for f in fixtures):
                    for wrapper in reversed(fixtures):
                        _test_func = wrapper(_test_func)
                    _test_func(test)
                    return
                with ExitStack() as stack:
                    for ctx in fixtures:
                        stack.enter_context(ctx)
                    _test_func(test)

            dic[name] = wrapper

        stack_holder = [ExitStack()]

        def setUpClass(cls, *arg, **kw):
            stack = stack_holder[0]
            with stack:
                for Ctx in self.fixtures['class']:
                    ctx = Ctx(cls)
                    stack.enter_context(ctx)
                stack_holder[0] = stack.pop_all()
        dic['setUpClass'] = classmethod(setUpClass)

        def tearDownClass(cls, *arg, **kw):
            stack = stack_holder[0]
            with stack:
                pass
        dic['tearDownClass'] = classmethod(tearDownClass)
        dic.update({
            'with_fixtures': self.fixture_names,
            'get_fixture': LazyFixture(self.fixtures['lazy']),
            'setUp': no_op, 'tearDown': no_op,
        })
        return dic

    def make_suite(self):
        dic = self.prepare_case()
        Case = type(self.klass.__name__, (self.klass,), dic)
        Case.__module__ = self.klass.__module__
        return unittest.TestSuite([Case(name) for name in self.names])


class ClassFixturesCanBeCallables(CaseBuilder):

    def runCase(self, testcase_cls, result):
        testcase_cls._result = result
        def func(cls):
            s = unittest.TestSuite(
                [cls(name) for name in self.names]
            )
            s(result)

        fixtures = [F(testcase_cls) for F in self.fixtures['class']]
        if not all(isinstance(f, ContextManager) for f in fixtures):
            for wrapper in reversed(fixtures):
                func = wrapper(func)
        else:
            @wraps(func)
            def func(testcase_cls, _func=func):
                with ExitStack() as stack:
                    for ctx in fixtures:
                        stack.enter_context(ctx)
                    return _func(testcase_cls)

        class Case(unittest.TestCase):
            def run(self, _result=None):
                if _result is None:
                    _result = self.defaultTestResult()
                unittest.TestCase.run(self, _result)
                result.failures += _result.failures
                result.errors += _result.errors
                result.expectedFailures += _result.expectedFailures
                result.unexpectedSuccesses += _result.unexpectedSuccesses

            def runCase(self):
                func(testcase_cls)

        Case = type(testcase_cls.__name__, (Case,), {})
        Case.__module__ = testcase_cls.__module__
        case = Case('runCase')
        case()

    def prepare_case(self):
        dic = {
            'get_fixture': LazyFixture(self.fixtures['lazy']),
            'with_fixtures': self.fixture_names,
            'setUp': no_op, 'tearDown': no_op,
            'setUpClass': classmethod(no_op), 'tearDownClass': classmethod(no_op),
        }

        for name in self.names:
            func = getattr(self.klass, name)
            if PY2:
                func = func.__func__
            @wraps(func)
            def wrapper(test, _test_func=func):
                fixtures = [F(test) for F in self.fixtures['test']]
                if not all(isinstance(f, ContextManager) for f in fixtures):
                    for wrapper in reversed(fixtures):
                        _test_func = wrapper(_test_func)
                    _test_func(test)
                    return
                with ExitStack() as stack:
                    for ctx in fixtures:
                        stack.enter_context(ctx)
                    _test_func(test)

            dic[name] = wrapper
        return dic

    def make_suite(self):
        dic = self.prepare_case()
        Case = type(self.klass.__name__, (self.klass,), dic)
        Case.__module__ = self.klass.__module__
        runCase = partial(self.runCase, Case)
        return unittest.TestSuite([runCase])


class FixtureManager(object):

    def __init__(self, testcase_cls, test_names, test_level_config=True):
        self.klass = testcase_cls
        self.names = test_names
        self.test_level_config = test_level_config

    def __iter__(self):
        configs = list(self.iter_test_configs())
        for names, config in configs:
            provider_sets = [l for l in self.iter_provider_sets(config) if l]
            for fixtures in product(*provider_sets):
                try:
                    fixtures = [
                        f for f in fixtures if f is not None
                        if not hasattr(f, 'validate_chain')
                        or f.validate_chain(fixtures, self.klass)
                    ]
                except ValidationError:
                    continue
                yield names, fixtures, config

    def iter_provider_sets(self, config,
                           pony_fixtures=pony_fixtures,
                           fixture_handlers=fixture_handlers,
                           fixture_providers=fixture_providers):
        if hasattr(config, 'pony_fixtures'):
            pony_fixtures = config.pony_fixtures
        else:
            pony_fixtures = list(pony_fixtures) + list(
                getattr(config, 'include_fixtures', ())
            )
        pony_fixtures = [
            p for p in pony_fixtures if p not in getattr(config, 'exclude_fixtures', ())
        ]
        if hasattr(config, 'lazy_fixtures'):
            pony_fixtures += [
                f for f in config.lazy_fixtures if f not in pony_fixtures
            ]
        if hasattr(config, 'fixture_providers'):
            fixture_providers = dict(fixture_providers)
            for key, providers in config.fixture_providers.items():
                if isinstance(providers, Mapping):
                    fixture_providers.setdefault(key, {}).update(providers)
                else:
                    fixture_providers[key] = {
                        k: v for k, v in fixture_providers[key].items()
                        if k in providers
                    }
        if hasattr(config, 'fixture_handlers'):
            fixture_handlers = dict(fixture_handlers, **config.fixture_handlers)

        for key in pony_fixtures:
            all_providers = fixture_providers[key]
            if not all_providers:
                yield ()
                continue
            handler = fixture_handlers.get(key)
            if handler:
                providers = handler(key, all_providers)
            else:
                providers = fixture_handlers['__default__'](key, all_providers)

            providers = list(providers)

            yield [
                fixture_providers[key][p]
                for p in providers
            ]

    def iter_test_configs(self):
        'yield names, config_obj'
        klass = self.klass
        if not self.test_level_config:
            yield self.names, klass
            return
        non_special = []
        for name in self.names:
            func = getattr(klass, name)
            if any(hasattr(func, attr) for attr in (
                'test_scoped', 'class_scoped', 'include_fixtures', 'exclude_fixtures',
                'pony_fixtures', 'fixture_providers',
            )):
                yield [name], merge_attrs(func, klass)
                continue
            non_special.append(name)
        if non_special:
            yield non_special, klass



