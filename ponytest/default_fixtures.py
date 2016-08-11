
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
    KEY = 'ipdb'

    # @with_cli_args
    # @click.option('--ipdb', 'debug', is_flag=True)
    # def handler(self, providers, debug):
    #     if debug:
    #         for p in self.providers:
    #             yield p

    # @Fixture.provider(KEY)
    # def provider(Test):
    #     if isinstance(Test, type):
    #         return ipdb_class_scope(Test)
    #     return ipdb_context(Test)

    # provider.enabled = False

    @Fixture.provider(KEY)
    class Provider(object):

        enabled = False

        def __init__(self, Test):
            self.Test = Test

        @property
        def weight(self):
            if isinstance(self.Test, type):
                return -10
            return 10

        def __enter__(self):
            pass

        def __exit__(self, *exc_info):
            from ipdb import post_mortem
            e, m, tb = exc_info
            if e and not e.__module__.startswith('unittest'):
                print(m.__repr__(), file=sys.stderr)
                post_mortem(tb)


# def ipdb_context(test):
#     from ipdb import post_mortem
#     try:
#         yield
#     except Exception as exc:
#         e, m, tb = sys.exc_info()
#         if not e.__module__.startswith('unittest'):
#             print(m.__repr__(), file=sys.stderr)
#             post_mortem(tb)
#         raise exc

# ipdb_context.weight = 10


# @contextmanager
# def ipdb_class_scope(cls):
#     with ipdb_context(cls):
#         yield

# ipdb_class_scope.weight = -10

# @with_cli_args
# @click.option('--ipdb', 'debug', is_flag=True)
# def enable_ipdb(debug):
#     if debug:
#         yield ipdb_context



# @with_cli_args
# @click.option('--ipdb', 'debug', is_flag=True)
# def enable_ipdb_all(key, providers, debug):
#     if debug:
#         for p in providers:
#             yield p

# from .config import fixture_handlers

# fixture_handlers['ipdb_all'] = enable_ipdb_all


# debugger_support = OrderedDict([
#     ('ipdb_all', enable_ipdb_all),
#     ('ipdb', enable_ipdb),
# ])

Ipdb()

debugger_support = {
    'test': ['ipdb'], 'class': ['ipdb']
}


