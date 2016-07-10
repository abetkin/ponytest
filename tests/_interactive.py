

# Not actually automatic tests
#

from contextlib import contextmanager


@contextmanager
def use_log(test):
    print('start logging')
    assert 0
    yield
    print('end logging')

use_log.class_scoped = True


import unittest

class TestDebug(unittest.TestCase):

    from ponytest import pony_fixtures
    pony_fixtures.append([use_log])


    @classmethod
    def setUpClass(cls):
        assert 0

    def test(self):
        pass

    def setUp(self):
        assert 0