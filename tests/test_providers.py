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
    KEY = 'myfixture'

    class Option(ContextDecorator):

        def __init__(self, test, name):
            self.name = name
            self.test = test

        def __enter__(self):
            self.test.option_value = self.name
            return 'value'

        __exit__ = lambda *args: None

        @classmethod
        def make(cls, name):
            ret = partial(cls, name=name)
            ret.KEY = 'myfixture'
            return ret

    Fixture.provider(KEY, '1')(partial(Option, name='1'))
    Fixture.provider(KEY, '2')(partial(Option, name='2'))
    # providers = {
    #     '1': partial(Option, name='1'),
    #     '2': partial(Option, name='2'),
    # }



class Test(unittest.TestCase):

    fixture_providers = {
        'myfixture': ['2']
    }

    pony_fixtures = {'test': [F()]}

    def test(self):
        self.assertEqual(self.option_value, '2')


class TestLazyFixture(unittest.TestCase):
    lazy_fixtures = ['myfixture']

    def test(self):
        # FIXME executes 8 times
        with self.get_fixture('myfixture') as value:
            self.assertIn(self.option_value, '12')
            self.assertEqual(value, 'value')


