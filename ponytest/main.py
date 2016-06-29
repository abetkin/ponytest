
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
    pony_contexts = deque()

    def _make_tests(self, names, klass, contexts):
        if not contexts:
            return [klass(name) for name in names]
        test_scoped = [] # also, layers can be case-scoped (= class-scoped)
        for Ctx in contexts:
            if getattr(Ctx, 'test_scoped', False):
                test_scoped.append(Ctx)

        dic = {}
        if test_scoped:
            stacks = {name: ExitStack() for name in names}

            _setUp = klass.setUp.__func__
            @wraps(_setUp)
            def setUp(test):
                stack = stacks[test._testMethodName]
                for Ctx in test_scoped:
                    ctx = Ctx(test)
                    stack.enter_context(ctx)
                with stack:
                    _setUp(test)
                    stacks[test._testMethodName] = stack.pop_all()
            dic['setUp'] = setUp

            _tearDown = klass.tearDown.__func__
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
                def wrapper(test, _wrapped=func, *arg, **kw):
                    stack = stacks[test._testMethodName]
                    with stack:
                        _wrapped(test, *arg, **kw)
                        stacks[test._testMethodName] = stack.pop_all()
                dic[name] = wrapper

        case_scoped = [Ctx for Ctx in contexts if Ctx not in test_scoped]

        if case_scoped:
            stack_holder = [ExitStack()]

            _setUpClass = klass.setUpClass.__func__
            @wraps(_setUpClass)
            def setUpClass(cls, *arg, **kw):
                stack = stack_holder[0]
                for L in case_scoped:
                    ctx = L(cls)
                    stack.enter_context(ctx)
                with stack:
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

        type_name = 'PONY_' + klass.__name__
        new_klass = type(type_name, (klass,), dic)
        return [new_klass(name) for name in names]


    def loadTestsFromTestCase(self, testCaseClass):
        assert not issubclass(testCaseClass, suite.TestSuite)
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        suites = []
        for chain in self.get_layers_chains(testCaseClass):
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

    def get_layers_chains(self, klass):
        layer_sets = []
        pony_contexts = getattr(klass, 'pony_contexts', self.pony_contexts)
        for ctx in pony_contexts:
            if not isinstance(ctx, Iterable):
                ctx = ctx()
            layers = tuple(ctx)
            if layers:
                layer_sets.append(layers)
        ret = []
        for layer_chain in product(*layer_sets):
            ret.append(
                tuple(layer_chain)
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

pony_contexts = TestLoader.pony_contexts

