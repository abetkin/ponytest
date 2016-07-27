
import unittest
from .main import FixtureManager, TestLoader, is_standalone_use
from .utils import with_metaclass, PY2


class Meta(type):

    def __new__(cls, name, bases, namespace):
        klass = super(Meta, cls).__new__(cls, name, bases, namespace)
        if namespace.get('disable_Meta'):
            return klass
        if not is_standalone_use():
            return klass
        mgr = FixtureManager(klass)
        fixture_chains = list(mgr.iter_fixture_chains())

        if not fixture_chains:
            return klass
        fixtures = fixture_chains[0]
        names = TestLoader().getTestCaseNames(klass)
        dic = mgr._prepare_standalone_case(fixtures, names)
        namespace.update(dic)
        return super(Meta, cls).__new__(cls, name, bases, namespace)



class TestCase(unittest.TestCase, metaclass=Meta):

    disable_Meta = True

    def __str__(self):
        return ' '.join([
            unittest.TestCase.__str__(self),
            '[%s]' % ', '.join(self.with_fixtures),
        ])


