import unittest
from functools import partial

import sys
PY2 = sys.version_info[0] == 2

if not PY2:
    from contextlib import contextmanager, ContextDecorator
else:
    from contextlib2 import contextmanager, ContextDecorator

from ponytest import Fixture

class F(Fixture):
    __key__ = 'providers.F'

class Option(ContextDecorator):

    def __init__(self, test, name):
        self.name = name
        self.test = test

    def __enter__(self):
        self.test.option_value = self.name
        return 'value'

    __exit__ = lambda *args: None


F.provider('1')(partial(Option, name='1'))
F.provider('2')(partial(Option, name='2'))



class Test(unittest.TestCase):

    fixture_providers = {
        'providers.F': ['2']
    }

    pony_fixtures = {'test': [F]}

    def test(self):
        self.assertEqual(self.option_value, '2')


class TestLazyFixture(unittest.TestCase):
    lazy_fixtures = ['providers.F']

    def test(self):
        with self.get_fixture('providers.F') as value:
            self.assertIn(self.option_value, '12')
            self.assertEqual(value, 'value')

