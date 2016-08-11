
from functools import wraps, partial
from itertools import product
from collections import deque, Iterable, Mapping, namedtuple

from .utils import PY2, ContextManager, ValidationError, add_metaclass, no_op, \
        merge_attrs, with_cli_args
import click
if not PY2:
    from contextlib import contextmanager, ExitStack, ContextDecorator
else:
    from contextlib2 import contextmanager, ExitStack, ContextDecorator

from .config import fixture_providers, fixture_handlers, pony_fixtures, provider_validators


import unittest

from .is_standalone import is_standalone_use



# def provider(key=None, provider=None, **kwargs):
#     def decorator(obj, key=key, provider=provider):
#         if key is None:
#             key = obj.KEY
#         elif not hasattr(obj, 'KEY'):
#             obj.KEY = key
#         else:
#             assert obj.KEY == key
#         if provider is None:
#             provider = getattr(obj, 'PROVIDER', 'default')
#         if not hasattr(obj, 'PROVIDER'):
#             obj.PROVIDER = provider
#         else:
#             assert obj.PROVIDER == provider
#         assert fixture_providers.get(key, {}).get(obj.PROVIDER, obj) is obj
#         fixture_providers.setdefault(key, {})[provider] = obj
#         for k, v in kwargs.items():
#             setattr(obj, k, v)
#         return obj
#     return decorator


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
        # try:
        #     fixtures['class'], fixtures['test'], fixtures['lazy']
        # except:
        #     fixtures = self._group_by_scope(testcase_cls, fixtures, config)
        self.fixtures = fixtures
        self.names = names
        self.config = config

    @classmethod
    def factory(cls, testcase_cls, fixtures, names, config):
        for F in fixtures['class']:
            if not isinstance(F(testcase_cls), ContextManager):
                builder = ClassFixturesCanBeCallables
                break
        else:
            builder = ClassFixturesAreContextManagers
        return builder(testcase_cls, fixtures, names, config)

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
    def _sorted(fixtures):
        return sorted(fixtures, key=lambda f: getattr(f, 'weight', 0))

    # @staticmethod
    # def _is_test_scoped(fixture, config):
    #     if fixture.KEY in getattr(config, 'test_scoped', ()):
    #         return True
    #     if fixture.KEY not in getattr(config, 'test_scoped', ()) \
    #             and  fixture.KEY in getattr(config, 'class_scoped', ()):
    #         return False
    #     return getattr(fixture, 'scope', 'test') == 'test'

    # @staticmethod
    # def _is_class_scoped(fixture, config):
    #     if fixture.KEY in getattr(config, 'class_scoped', ()):
    #         return True
    #     if fixture.KEY not in getattr(config, 'class_scoped', ()) \
    #             and  fixture.KEY in getattr(config, 'test_scoped', ()):
    #         return False
    #     return getattr(fixture, 'scope', 'test') == 'class'

    # @staticmethod
    # def _is_lazy(fixture, config):
    #     if fixture.KEY in getattr(config, 'lazy_fixtures', ()):
    #         return True
    #     return getattr(fixture, 'scope', 'test') == 'lazy'

    # @classmethod
    # def _group_by_scope(cls, klass, fixtures, config):
    #     import ipdb; ipdb.set_trace()
    #     test_scoped = []
    #     class_scoped = []
    #     lazy_fixtures = []

    #     for F in fixtures:
    #         if cls._is_lazy(F, config):
    #             lazy_fixtures.append(F)
    #             continue
    #         if cls._is_test_scoped(F, config):
    #             test_scoped.append(F)
    #         if cls._is_class_scoped(F, config):
    #             class_scoped.append(F)

    #     _setUp = klass.setUp
    #     if PY2:
    #         _setUp = _setUp.__func__
    #     _tearDown = klass.tearDown
    #     if PY2:
    #         _tearDown = _tearDown.__func__

    #     test_scoped.append(
    #         SetupTeardownFixture(_setUp, _tearDown)
    #     )

    #     _setUpClass = klass.setUpClass.__func__
    #     _tearDownClass = klass.tearDownClass.__func__
    #     class_scoped.append(
    #         SetupTeardownFixture(_setUpClass, _tearDownClass)
    #     )
    #     ret ={
    #         'test': cls._sort(test_scoped),
    #         'class': cls._sort(class_scoped),
    #         'lazy': cls._sort(lazy_fixtures),
    #     }
    #     print('ret', ret)
    #     return ret


class ClassFixturesAreContextManagers(CaseBuilder):

    def prepare_case(self):
        dic = {}

        for name in self.names:
            func = getattr(self.klass, name)
            if PY2:
                func = func.__func__
            @wraps(func)
            def wrapper(test, _test_func=func):
                fixtures = self._sorted(
                    [F(test) for F in self.fixtures['test']]
                )
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
            fixtures = self._sorted(
                [Ctx(cls) for Ctx in self.fixtures['class']]
            )
            with stack:
                for ctx in fixtures:
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

        fixtures = self._sorted(
            [F(testcase_cls) for F in self.fixtures['class']]
        )
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
                fixtures = self._sorted(
                    [F(test) for F in self.fixtures['test']]
                )
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

SCOPES = ('test', 'class', 'lazy')

class FixtureManager(object):

    def __init__(self, testcase_cls, test_names, test_level_config=True):
        self.klass = testcase_cls
        self.names = test_names
        self.test_level_config = test_level_config

    def get_fixtures(self, config, scope):
        config_fixtures = getattr(config, 'pony_fixtures', {})
        fixtures = config_fixtures.get(scope, ()) or pony_fixtures.get(scope, ())
        return [
            Fixture._registry[f] if isinstance(f, str) else f
            for f in fixtures
        ]

    def __iter__(self):
        configs = list(self.iter_test_configs())
        ScopedProvider = namedtuple('ScopedProvider', ['scope', 'provider'])
        for names, config in configs:
            provider_sets = [
                [ScopedProvider(scope, p) for p in providers]
                for scope in SCOPES
                for providers in self.iter_provider_sets(config, scope)
                if providers
            ]

            for chain in product(*provider_sets):
                fixtures = {}
                for scope in SCOPES:
                    fixtures[scope] = [f.provider for f in chain if f.scope == scope]
                    pony_fixtures = self.get_fixtures(config, scope)
                    if not all(f.validate_fixtures(fixtures[scope], config)
                               for f in pony_fixtures):
                        break
                else:
                    yield names, fixtures, config

    def iter_provider_sets(self, config, scope):
        pony_fixtures = self.get_fixtures(config, scope)
        if hasattr(config, 'include_fixtures'):
            pony_fixtures.extend(
                [self._registry[f] for f in config.include_fixtures]
            )
        if hasattr(config, 'exclude_fixtures'):
            pony_fixtures = [
                f for f in pony_fixtures if f.KEY not in config.exclude_fixtures
            ]
        for f in pony_fixtures:
            yield f._get_providers(config)

    CONFIG_ATTRS = (
        'pony_fixtures', 'include_fixtures', 'exclude_fixtures',
        'fixture_providers', 'fixture_handlers', 'fixture_validators',
    )

    def iter_test_configs(self):
        'yield names, config_obj'
        klass = self.klass
        if not self.test_level_config:
            yield self.names, klass
            return
        non_special = []
        for name in self.names:
            func = getattr(klass, name)
            if any(hasattr(func, attr) for attr in self.CONFIG_ATTRS):
                yield [name], merge_attrs(func, klass)
                continue
            non_special.append(name)
        if non_special:
            yield non_special, klass


class Fixture(object):
    _registry = {}
    KEY = None

    def __new__(cls, *args, **kw):
        ret = super(Fixture, cls).__new__(cls, *args, **kw)
        assert ret.KEY
        cls._registry[ret.KEY] = ret
        if hasattr(ret, 'default_provider') and not hasattr(ret, 'providers'):
            ret.provider()(ret.default_provider)
        return ret

    def handler(self, **kwargs):
        providers = self.providers
        key = self.KEY
        formatted_key =  key.replace('_', '-')
        option = ''.join(('--', formatted_key))
        no_option = '-'.join(('--no', formatted_key))
        if len(providers) == 1:
            @with_cli_args
            @click.option(option, 'enabled', is_flag=True)
            @click.option(no_option, 'disabled', is_flag=True)
            def single_provider(enabled, disabled):
                if disabled:
                    return ()
                provider_key = next(p for p in providers)
                if enabled:
                    return (provider_key,)
                provider = providers[provider_key]
                if getattr(provider, 'enabled', True):
                    return (provider_key,)
                return ()
            return single_provider()

        @with_cli_args
        @click.option(option, 'included', multiple=True)
        @click.option(no_option, 'excluded', multiple=True)
        def multiple_providers(included, excluded, providers=providers):
            providers = {k: v for k, v in providers.items()
                        if not included or k in included
                        if not excluded or k not in excluded}
            if included or excluded:
                return providers
            return (key for key, p in providers.items()
                    if getattr(p, 'enabled', True))

        return multiple_providers()


    _providers = {}

    @property
    def providers(self):
        return self._providers[self.KEY]

    @classmethod
    def provider(cls, key, **kwargs):
        def decorator(obj, provider='default'):
            for k, v in kwargs.items():
                setattr(obj, k, v)
            cls._providers.setdefault(key, {})[provider] = obj
            return obj
        return decorator

    def validate_fixtures(self, fixtures, config):
        return True

    def _get_providers(self, config):
        providers = self.providers
        if hasattr(config, 'fixture_providers'):
            use_providers = config.fixture_providers.get(self.KEY)
            if isinstance(use_providers, Mapping):
                providers = dict(providers, **use_providers)
            else:
                providers = {
                    k: v for k, v in self.providers.items()
                    if k in use_providers
                }
        if hasattr(config, 'fixture_handlers') and config.fixture_handlers.get(self.KEY):
            handler = config.fixture_handlers[self.KEY]
        else:
            handler = self.handler
        if not self.providers:
            return ()
        providers = handler(key=self.KEY, providers=self.providers)
        return [
            self.providers[p] for p in providers
        ]
