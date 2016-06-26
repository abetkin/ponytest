'''
Command to launch tests:
python -m pony.testing <args> --- <OPTIONS>
'''

from unittest import suite, loader, TestCase as _TestCase, TestProgram as _TestProgram
from unittest.loader import TestLoader as _TestLoader

from functools import wraps
import logging
from contextlib import contextmanager
import sys

from pony.py23compat import PY2, ContextDecorator

import click
from pony.click_utils import with_cli_args

from pony.utils import cached_property, class_cached_property


import unittest


from itertools import product


class Layer(object):
    '''
    Marker class
    '''
    # TODO with metaclass ABCMeta ?


from collections import deque

class TestLoader(_TestLoader):
    default_layers = deque()

    def _make_tests(self, names, klass, layers):

        import ipdb; ipdb.set_trace()
        context_mgrs = []
        for L in layers:
            if not isinstance(L, type) or not issubclass(L, Layer):
                context_mgrs.append(L)
        dic = {}
        for name in names:
            if not context_mgrs:
                break
            func = getattr(klass, name)
            if PY2:
                func = func.__func__
            @wraps(func)
            def wrapper(test, *arg, _wrapped=func, **kw):
                for L in context_mgrs:
                    ctx = L(test)
                    _wrapped = ctx(_wrapped)
                return _wrapped(test, *arg, **kw)
            dic[name] = wrapper
        def get_mixins():
            for L in layers:
                if L in context_mgrs:
                    continue
                dic = {}
                for key in ('setUp', 'tearDown', 'setUpClass', 'tearDownClass'):
                    for cls in Layer.__mro__:
                        value = cls.__dict__.get(key)
                        if value:
                            dic[key] = value
                            break
                if not dic:
                    continue
                type_name = ''.join((Layer.__name__, 'Mixin'))
                yield type(type_name, (object,), dic)

        mixins = tuple(get_mixins())
        if not mixins and not dic:
            return [klass(name) for name in names]
        bases = mixins + (klass,)
        type_name = 'PONY_' + klass.__name__
        new_klass = type(type_name, bases, dic)
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
        print(':', getattr(klass, 'layers', self.default_layers))
        for ctx in getattr(klass, 'layers', self.default_layers):
            try:
                layer_sets.append(tuple(ctx))
                continue
            except TypeError:
                pass
            if hasattr(ctx, 'factory'):
                layer_sets.append(
                    tuple(ctx.factory())
                )
            else:
                layer_sets.append([ctx])
        ret = []
        for layer_chain in product(*layer_sets):
            ret.append(
                tuple(layer_chain)
            )
        return ret


class TestProgram(_TestProgram):
    def __init__(self, *args, **kwargs):
        try:
            kwargs['argv'] = sys.argv[:sys.argv.index('---')]
        except ValueError:
            pass
        kwargs['testLoader'] = TestLoader()
        super(TestProgram, self).__init__(*args, **kwargs)


default_layers = TestLoader.default_layers

