
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



@provider('ipdb', weight=10)
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


@provider('ipdb_all', class_scoped=True, weight=-10)
@contextmanager
def ipdb_class_scope(cls):
    with ipdb_context(cls):
        yield


@with_cli_args
@click.option('--ipdb', 'debug', is_flag=True)
def enable_ipdb(debug):
    if debug:
        yield ipdb_context



@with_cli_args
@click.option('--ipdb', 'debug', is_flag=True)
def enable_ipdb_all(debug):
    if debug:
        yield ipdb_class_scope



debugger_support = OrderedDict([
    ('ipdb_all', enable_ipdb_all),
    ('ipdb', enable_ipdb),
])

pony_fixtures.update(debugger_support)
