
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
    __key__ = 'simplest'

    @Fixture.provider(__key__)
    @contextmanager
    def add_attr(cls):
        cls.added_attribute = 'attr'
        yield


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

    class Simplest(Fixture):
        __key__ = 'cli.simplest'

        @Fixture.provider(__key__)
        @contextmanager
        def simplest(test):
            test.output = ['item']
            yield


    @class_property
    def cli_handle(cls, **kwargs):



        @with_cli_args
        @click.option('--on', 'is_on', is_flag=True)
        def handle(is_on, **kwargs): # TODO as keywords
            if is_on:
                yield 'default'


        return handle

    pony_fixtures = {'test': [Simplest]}

    @class_property
    def fixture_handlers(cls):
        return {'cli.simplest': cls.cli_handle}

    def test(self):
        self.assertFalse(self.output)



class TestCliPos(TestCliNeg):

    @class_property
    def cli_handle(cls):
        def handle(**kwargs):
            try:
                sys.argv.append('--on')
                return TestCliNeg.cli_handle(**kwargs)
            finally:
                sys.argv.remove('--on')
        return handle

    def test(self):
        self.assertTrue(self.output)


class TestExcludeFixtures(TestCase):

    class F(Fixture):
        __key__ = 'F'

    @Fixture.provider('F')
    def raises_exc(test):
        raise Exception

    exclude_fixtures = {'test': ['F']}
    pony_fixtures = {'test': [F]}

    def test(self):
        self.assertTrue(1)


class TestLevelConfig(TestCase):

    class F(Fixture):
        __key__ = 'tlf'

        @Fixture.provider(__key__, 'p1')
        @contextmanager
        def p1(test):
            test.attr = 1
            yield

        @Fixture.provider(__key__, 'p2')
        @contextmanager
        def p2(test):
            test.attr = 2
            yield

    pony_fixtures = {'test': [F]}
    fixture_providers = {'tlf': ['p1']}

    def test_1(self):
        self.assertEqual(self.attr, 1)

    def test_2(self):
        from ponytest.is_standalone import is_standalone_use
        if is_standalone_use():
            self.assertEqual(self.attr, 1) # test-level config is not supported
        else:
            self.assertEqual(self.attr, 2)
    test_2.fixture_providers = {'tlf': ['p2']}