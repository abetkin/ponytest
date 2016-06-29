

# Not actually automatic tests
#

from contextlib import contextmanager


@contextmanager
def use_log(test):
    raise Exception

use_log.test_scoped = True


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