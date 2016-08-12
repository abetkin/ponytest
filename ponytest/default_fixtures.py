
from __future__ import print_function
import sys
from collections import OrderedDict

from .main import pony_fixtures, Fixture
from .utils import with_cli_args, PY2


import click

if not PY2:
    from contextlib import contextmanager
else:
    from contextlib2 import contextmanager



class Ipdb(Fixture):
    __key__ = 'ipdb'


@Ipdb.provider()
class IpdbProvider(object):

    enabled = False
    weight = -10

    def __init__(self, Test):
        self.Test = Test

    def __enter__(self):
        pass

    def __exit__(self, *exc_info):
        from ipdb import post_mortem
        e, m, tb = exc_info
        if e and not e.__module__.startswith('unittest'):
            print(m.__repr__(), file=sys.stderr)
            post_mortem(tb)


debugger_support = {
    'test': ['ipdb'], 'class': ['ipdb']
}


