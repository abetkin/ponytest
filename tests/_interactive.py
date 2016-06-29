

# Not actually automatic tests
#

import unittest

class TestDebug(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        assert 0

    def test(self):
        pass

    def setUp(self):
        assert 0