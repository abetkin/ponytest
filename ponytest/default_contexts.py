
from .main import pony_fixtures
from .utils import with_cli_args, PY2


# register default layers

from functools import partial
import click

if not PY2:
    from contextlib import contextmanager
else:
    from contextlib2 import contextmanager


@contextmanager
def ipdb_context(cls):
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

@with_cli_args
@click.option('--ipdb', 'debug', is_flag=True)
def use_ipdb(debug):
    if debug:
        yield ipdb_context

def use_ipdb_at_test_scope():
    for mgr in use_ipdb():
        mgr = partial(mgr)
        mgr.test_scoped = True
        yield mgr


pony_fixtures.extend([
    use_ipdb,
    use_ipdb_at_test_scope,
])
