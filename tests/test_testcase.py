
from ponytest import TestCase

from contextlib import contextmanager

@contextmanager
def simplest(cls):
    assert isinstance(cls, type)
    cls.added_attribute = 'attr'
    yield

simplest.scope = 'class'
simplest.fixture_name = 'SI'

from ponytest.is_standalone import is_standalone_use
if is_standalone_use():

    class Test1(TestCase):

        pony_fixtures = enumerate([
            [simplest]
        ])

        def test(self):
            self.assertTrue(self.added_attribute)