import unittest
import test_forking


class Test(unittest.TestCase):

    pony_fixtures = {
        'myfixture': ['2']
    }

    def test(self):
        self.assertEqual(self.option_value, '2')




class TestLazyFixture(unittest.TestCase):
    lazy_fixtures = ['myfixture']

    def test(self):
        with self.get_fixture('myfixture') as value:
            self.assertIn(self.option_value, '12')
            self.assertEqual(value, 'value')


