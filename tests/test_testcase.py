
from ponytest import TestCase, Fixture

from contextlib import contextmanager

class F1(Fixture):
    __key__ = 'key1'

    @Fixture.provider(__key__)
    @contextmanager
    def simplest(cls):
        assert isinstance(cls, type)
        cls.added_attribute = 'attr'
        yield




from ponytest.is_standalone import is_standalone_use
if is_standalone_use():

    class Test1(TestCase):

        pony_fixtures = {'class': [F1()]}

        def test(self):
            self.assertTrue(self.added_attribute)