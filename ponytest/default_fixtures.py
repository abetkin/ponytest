
from .main import pony_fixtures
from .utils import with_cli_args, PY2


from functools import partial
import click

if not PY2:
    from contextlib import contextmanager
else:
    from contextlib2 import contextmanager


@contextmanager
def ipdb_fixture(test):
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
        yield ipdb_fixture

def use_ipdb_at_class_scope():
    for mgr in use_ipdb():
        mgr = partial(mgr)
        mgr.class_scoped = True
        yield mgr


pony_fixtures.extendleft([
    use_ipdb_at_class_scope,
    use_ipdb,
])
