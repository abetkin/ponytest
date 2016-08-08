
from __future__ import print_function
import sys
from collections import OrderedDict

from .main import pony_fixtures, provider
from .utils import with_cli_args, PY2


import click

if not PY2:
    from contextlib import contextmanager
else:
    from contextlib2 import contextmanager



@provider('ipdb', weight=10, enabled=False)
@contextmanager
def ipdb_context(test):
    from ipdb import post_mortem
    try:
        yield
    except Exception as exc:
        e, m, tb = sys.exc_info()
        if not e.__module__.startswith('unittest'):
            print(m.__repr__(), file=sys.stderr)
            post_mortem(tb)
        raise exc


@provider('ipdb_all', scope='class', weight=-10, enabled=False)
@contextmanager
def ipdb_class_scope(cls):
    with ipdb_context(cls):
        yield


# @with_cli_args
# @click.option('--ipdb', 'debug', is_flag=True)
# def enable_ipdb(debug):
#     if debug:
#         yield ipdb_context



@with_cli_args
@click.option('--ipdb', 'debug', is_flag=True)
def enable_ipdb_all(key, providers, debug):
    if debug:
        for p in providers:
            yield p

from .config import fixture_handlers

fixture_handlers['ipdb_all'] = enable_ipdb_all


# debugger_support = OrderedDict([
#     ('ipdb_all', enable_ipdb_all),
#     ('ipdb', enable_ipdb),
# ])

debugger_support = [
    'ipdb_all', 'ipdb'
]


