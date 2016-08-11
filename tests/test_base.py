
from functools import wraps
import click
from ponytest import with_cli_args, class_property, pony_fixtures, TestCase, Fixture

import sys
PY2 = sys.version_info[0] == 2

if not PY2:
    from contextlib import contextmanager, ContextDecorator
else:
    from contextlib2 import contextmanager, ContextDecorator


import unittest
import collections


class Simplest(Fixture):
    KEY = 'simplest'

    @Fixture.provider(KEY)
    @contextmanager
    def default_provider(cls):
        cls.added_attribute = 'attr'
        yield


Simplest()

class TestCaseScoped(TestCase):

    pony_fixtures = {'class': ['simplest']}

    def test(self):
        self.assertTrue(self.added_attribute)
        self.assertNotIn('added_attribute', self.__dict__)


class TestTestScoped(TestCase):

    pony_fixtures = {'test': ['simplest']}


    def test(self):
        self.assertIn('added_attribute', self.__dict__)


class TestCliNeg(TestCase):

    output = ()

    @contextmanager
    def simplest(test):
        test.output = ['item']
        yield

    fixture_providers = {'simplest': {0: simplest}}

    @class_property
    def cli_handle(cls):



        @with_cli_args
        @click.option('--on', 'is_on', is_flag=True)
        def handle(providers, is_on): # TODO as keywords
            if is_on:
                yield 0


        return handle

    pony_fixtures = ['simplest']

    @class_property
    def fixture_handlers(cls):
        return {'simplest': cls.cli_handle}

    def test(self):
        self.assertFalse(self.output)



class TestCliPos(TestCliNeg):

    @class_property
    def cli_handle(cls):
        def handle(providers):
            try:
                sys.argv.append('--on')
                return TestCliNeg.cli_handle(providers)
            finally:
                sys.argv.remove('--on')
        return handle

    def test(self):
        self.assertTrue(self.output)


class TestExcludeFixtures(TestCase):

    def raises_exc(test):
        raise Exception

    exclude_fixtures = ['F']
    fixture_providers = {
        'F': {'exc': raises_exc}
    }
    pony_fixtures = ['F']

    def test(self):
        self.assertTrue(1)


class TestLevelConfig(TestCase):

    @contextmanager
    def f1(test):
        test.attr = 1
        yield

    @contextmanager
    def f2(test):
        test.attr = 2
        yield

    fixture_providers = {'f': {0: f1}}
    pony_fixtures = ['f']

    def test_1(self):
        self.assertEqual(self.attr, 1)

    def test_2(self):
        from ponytest.is_standalone import is_standalone_use
        if is_standalone_use():
            self.assertEqual(self.attr, 1) # test-level config is not supported
        else:
            self.assertEqual(self.attr, 2)
    test_2.fixture_providers = {'f': {0: f2}}

    del f1, f2