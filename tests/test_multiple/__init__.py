import click
from ponytest.utils import with_cli_args, class_property

import sys
PY2 = sys.version_info[0] == 2

if not PY2:
    from contextlib import contextmanager, ContextDecorator
else:
    from contextlib2 import contextmanager, ContextDecorator

import unittest
from functools import partial

class TestMultiple(unittest.TestCase):

    output = []

    @classmethod
    def cli_handle(cls):
        @contextmanager
        def simplest(test, option=None):
            if option:
                test.option_value = option
            yield

        @with_cli_args
        @click.option('-o', '--option', 'options', multiple=True)
        def handle(options):
            for option in options:
                yield partial(simplest, option=option)

        return handle()

    @class_property
    def pony_fixtures(cls):
        try:
            length = len(sys.argv)
            sys.argv.extend(['-o', '1', '-o', '2'])
            return [
                tuple(cls.cli_handle())
            ]
        finally:
            sys.argv = sys.argv[:length]


    def test(self):
        self.output.append(
            self.option_value
        )

from unittest.suite import TestSuite

def load_tests(loader, tests, *argz):

    class Check(unittest.TestCase):
        def runTest(self):
            output = TestMultiple.output
            self.assertSetEqual(set(output), set('12'))


    return TestSuite([tests, Check()])