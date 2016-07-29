
from functools import wraps
import click
from ponytest import with_cli_args, class_property, pony_fixtures, TestCase

import sys
PY2 = sys.version_info[0] == 2

if not PY2:
    from contextlib import contextmanager, ContextDecorator
else:
    from contextlib2 import contextmanager, ContextDecorator


import unittest
import collections

class TestCaseScoped(TestCase):

    @contextmanager
    def simplest(cls):
        assert isinstance(cls, type)
        cls.added_attribute = 'attr'
        yield

    simplest.class_scoped = True

    pony_fixtures = enumerate([
        [simplest]
    ])

    del simplest

    def test(self):
        self.assertTrue(self.added_attribute)
        self.assertNotIn('added_attribute', self.__dict__)


class TestTestScoped(TestCase):

    @contextmanager
    def simplest(test):
        assert isinstance(test, unittest.TestCase)
        test.added_attribute = 'attr'
        yield

    pony_fixtures = enumerate([
        [simplest]
    ])


    def test(self):
        self.assertIn('added_attribute', self.__dict__)


class TestCliNeg(TestCase):

    output = ()

    @class_property
    def cli_handle(cls):

        @contextmanager
        def simplest(test):
            test.output = ['item']
            yield

        @with_cli_args
        @click.option('--on', 'is_on', is_flag=True)
        def handle(is_on):
            if is_on:
                yield simplest


        return handle


    @class_property
    def pony_fixtures(cls):
        return enumerate([cls.cli_handle])

    def test(self):
        self.assertFalse(self.output)



class TestCliPos(TestCliNeg):

    @class_property
    def cli_handle(cls):
        def handle():
            try:
                sys.argv.append('--on')
                return TestCliNeg.cli_handle()
            finally:
                sys.argv.remove('--on')
        return handle

    def test(self):
        self.assertTrue(self.output)


class TestExcludeFixtures(TestCase):

    def raises_exc(test):
        raise Exception

    exclude_fixtures = ['F']
    pony_fixtures = {
        'F': [raises_exc]
    }
    del raises_exc

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

    update_fixtures = {0: [f1]}

    def test_1(self):
        self.assertEqual(self.attr, 1)
    
    def test_2(self):
        self.assertEqual(self.attr, 2)
    test_2.update_fixtures = {0: [f2]}

    del f1, f2