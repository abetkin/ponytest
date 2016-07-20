

# Not actually automatic tests
#

from ponytest.utils import PY2

if PY2:
    from contextlib2 import contextmanager
else:
    from contextlib import contextmanager

from ponytest import pony_fixtures, provider

from collections import OrderedDict
from copy import copy

@provider('log', class_scoped = True)
@contextmanager
def use_log(test):
    print('start logging')
    assert 0
    yield
    print('end logging')



import unittest

class TestDebug(unittest.TestCase):

    pony_fixtures = copy(pony_fixtures)
    pony_fixtures['log'] = [use_log]


    @classmethod
    def setUpClass(cls):
        assert 0

    def test(self):
        pass

    def setUp(self):
        assert 0


class NoIpdb(TestDebug):

    pony_fixtures = OrderedDict(pony_fixtures,
        ipdb_all = (), ipdb = (), log = True,
    )