
from functools import wraps
import click
from ponytest import with_cli_args, class_property, pony_fixtures

import sys
PY2 = sys.version_info[0] == 2

if not PY2:
    from contextlib import contextmanager, ContextDecorator
else:
    from contextlib2 import contextmanager, ContextDecorator


import unittest
import collections

from copy import copy

class TestCaseScoped(unittest.TestCase):

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


class TestTestScoped(unittest.TestCase):

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


class TestCliNeg(unittest.TestCase):

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
                return super(TestCliPos, cls).cli_handle()
            finally:
                sys.argv.remove('--on')
        return handle

    def test(self):
        self.assertTrue(self.output)


class TestExcludeFixtures(unittest.TestCase):

    def raises_exc(test):
        raise Exception

    # exclude_fixtures = ['F']
    pony_fixtures = {
        'F': [raises_exc]
    }
    del raises_exc

    def test(self):
        self.assertTrue(1)