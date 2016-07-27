
from ponytest import TestCase

from contextlib import contextmanager

@contextmanager
def simplest(cls):
    assert isinstance(cls, type)
    cls.added_attribute = 'attr'
    yield

simplest.class_scoped = True
simplest.fixture_name = 'SI'



class Test1(TestCase):

    pony_fixtures = enumerate([
        [simplest]
    ])

    def test(self):
        print(self.added_attribute)
        assert 0