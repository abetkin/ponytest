
from functools import wraps, partial
from itertools import product, groupby
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
            F = next(f for f in self.fixtures if f.__provides__ == name)
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

    def __iter__(self):
        configs = list(self.iter_test_configs())
        for names, config in configs:
            all_fixtures = tuple(self.iter_fixtures(config))
            def provider_sets():
                for scope, f in all_fixtures:
                    items = f._get_providers(config)
                    if items:
                        yield [(scope, i) for i in items]
            provider_sets = tuple(provider_sets())

            for chain in product(*provider_sets):
                chain = sorted(chain)
                fixtures = {scope: () for scope in SCOPES}
                for scope, items in groupby(chain, lambda f: f[0]):
                    fixtures[scope] = [i[1] for i in items]

                if not all(f.validate_fixtures(fixtures, config)
                        for scope, f in all_fixtures):
                    continue
                yield names, fixtures, config

    def iter_fixtures(self, config):
        for scope in ['test', 'class']:
            config_fixtures = getattr(config, 'pony_fixtures', {})
            fixtures = config_fixtures.get(scope, ()) or pony_fixtures.get(scope, ())
            include_fixtures = getattr(config, 'include_fixtures', {}).get(scope, ())
            fixtures.extend(include_fixtures)
            exclude_fixtures = getattr(config, 'exclude_fixtures', {}).get(scope, ())
            if exclude_fixtures:
                fixtures = [
                    f for f in fixtures if f not in exclude_fixtures
                ]
            for F in fixtures:
                if not isinstance(F, type):
                    F = Fixture._registry[F]
                yield scope, F()
        for F in getattr(config, 'lazy_fixtures', ()):
            if not isinstance(F, type):
                F = Fixture._registry[F]
            yield 'lazy', F()

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


class FixtureMeta(type):

    def __new__(cls, name, bases, namespace):
        klass = super(FixtureMeta, cls).__new__(cls, name, bases, namespace)
        if namespace.get('disable_FixtureMeta'):
            return klass
        key = namespace.get('__key__')
        if key:
            klass._registry[key] = klass
        return klass

    def __hash__(cls):
        return hash(cls.__key__)

    def __eq__(cls, other):
        return hash(cls) == hash(other)


@add_metaclass(FixtureMeta)
class Fixture(object):
    disable_FixtureMeta = True

    _registry = {}
    __key__ = None

    def handler(self, providers, **kwargs):
        key = self.__key__
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
        return self._providers.setdefault(self.__key__, {})

    @classmethod
    def provider(cls, key, name='default', **kwargs):
        def decorator(obj):
            for k, v in kwargs.items():
                setattr(obj, k, v)
            cls._providers.setdefault(key, {})[name] = obj
            obj.__provides__ = key
            return obj
        return decorator

    def validate_fixtures(self, fixtures, config):
        return True

    def _get_providers(self, config):
        providers = self.providers
        if hasattr(config, 'fixture_providers'):
            use_providers = config.fixture_providers.get(self.__key__)
            if use_providers:
                providers = {
                    k: v for k, v in self.providers.items()
                    if k in use_providers
                }
        if hasattr(config, 'fixture_handlers') and config.fixture_handlers.get(self.__key__):
            handler = config.fixture_handlers[self.__key__]
        else:
            handler = self.handler
        if not self.providers:
            return ()
        providers = handler(key=self.__key__, providers=providers)
        return [
            self.providers[p] for p in providers
        ]
