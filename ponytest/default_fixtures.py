
from .main import pony_fixtures, provider
from .utils import with_cli_args, PY2


from functools import partial
import click

if not PY2:
    from contextlib import contextmanager
else:
    from contextlib2 import contextmanager

@provider('ipdb', weight=10)
@contextmanager
def ipdb_context(test):
    import ipdb
    raised = []
    with ipdb.launch_ipdb_on_exception():
        try:
            yield
        except Exception as exc:
            raised.append(exc)
            raise
    if raised:
        raise raised[0]

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
@click.option('--ipdb-all', 'debug', is_flag=True)
def enable_ipdb_all(debug):
    if debug:
        yield ipdb_class_scope



pony_fixtures.update({
    'ipdb_all': enable_ipdb_all,
    'ipdb': enable_ipdb,
})
