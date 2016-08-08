

# Not actually automatic tests
#

from ponytest.utils import PY2

if PY2:
    from contextlib2 import contextmanager
else:
    from contextlib import contextmanager

from ponytest import pony_fixtures, provider, TestCase

from collections import OrderedDict

@provider('log', scope='class')
@contextmanager
def use_log(test):
    print('start logging')
    assert 0
    yield
    print('end logging')



import unittest

class TestDebug(unittest.TestCase):

    include_fixtures = ['log']

    @classmethod
    def setUpClass(cls):
        assert 0

    def test(self):
        pass

    def setUp(self):
        assert 0


class NoIpdb(TestDebug):

    include_fixtures = ['log']

    fixture_providers = dict(
        ipdb_all = (), ipdb = (),
    )


class TestTestRunCount(TestCase):

    def test(self):
        self.assertTrue(1)

    def setUp(self):
        self.assertTrue(0)

    def test_failing(self):
        self.assertTrue(0)


    @classmethod
    def setUpClass(cls):
        assert 0

