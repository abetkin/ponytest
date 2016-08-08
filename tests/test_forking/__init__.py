import click
from ponytest import with_cli_args, class_property, pony_fixtures, fixture_providers as providers

import sys
PY2 = sys.version_info[0] == 2

if not PY2:
    from contextlib import contextmanager, ContextDecorator
else:
    from contextlib2 import contextmanager, ContextDecorator

import unittest
from functools import partial

class Option(ContextDecorator):
    KEY = 'myfixture'

    def __init__(self, test, name):
        self.name = name
        self.test = test

    def __enter__(self):
        self.test.option_value = self.name
        return 'value'

    __exit__ = lambda *args: None





class TestMultiple(unittest.TestCase):

    class Case(unittest.TestCase):
        def runTest(self): pass

    global asserts
    asserts = Case()


    output = []

    fixture_providers = {
        'myfixture': {
            '1': partial(Option, name='1'),
            '2': partial(Option, name='2'),

        }
    }

    pony_fixtures = ['myfixture']

    def test(self):
        self.output.append(self.option_value)


def load_tests(loader, tests, *argz):
    class Check(unittest.TestCase):
        def runTest(self):
            output = TestMultiple.output
            self.assertSetEqual(set(output), set('12'))

    from unittest import TestSuite
    return TestSuite([tests, Check()])
