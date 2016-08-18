
import sys
from unittest import suite, TestProgram as _TestProgram
from unittest.loader import TestLoader as _TestLoader

from .main import FixtureManager, CaseBuilder

import types
import unittest



class TestLoader(_TestLoader):

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

            fixture_mgr = FixtureManager(parent, [name])

            fixture_mgr = list(fixture_mgr)
            if not fixture_mgr:
                # TODO
                return self.suiteClass([])

            suites = []
            for _, fixtures, config, fixture_names in fixture_mgr:
                builder = CaseBuilder.factory(parent, fixtures, [name], config, fixture_names)
                s = builder.make_suite()
                suites.append(s)
            if not suites:
                return super(TestLoader, self).loadTestsFromName(
                    name, module
                )
            if len(suites) > 1:
                return self.suiteClass(suites)
            return suites[0]

    def loadTestsFromTestCase(self, testCaseClass):
        assert not issubclass(testCaseClass, suite.TestSuite)
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        fixture_mgr = FixtureManager(testCaseClass, testCaseNames)
        fixture_mgr = list(fixture_mgr)
        if not fixture_mgr:
            # TODO
            return self.suiteClass([])
        suites = []
        for names, fixtures, config, fixture_names in fixture_mgr:
            'TODO'



        # if not fixture_chains:
        #     return super(TestLoader, self).loadTestsFromTestCase(testCaseClass)

            builder = CaseBuilder.factory(testCaseClass, fixtures, names, config, fixture_names)
            s = builder.make_suite()
            suites.append(s)
        if len(suites) > 1:
            ret = self.suiteClass(suites)
        else:
            ret = suites[0]
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


