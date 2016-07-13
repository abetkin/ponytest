
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
@click.option('--ipdb-all', 'debug', flag_value='all')
@click.option('--ipdb', 'debug', flag_value='tests')
def use_ipdb(debug):
    if debug == 'tests':
        yield ipdb_fixture
        ipdb_fixture.weight = 10
    elif  debug == 'all':
        yield ipdb_fixture
        ipdb_fixture.weight = -10


def use_ipdb_at_class_scope():
    for mgr in use_ipdb():
        weight = getattr(mgr, 'weight', None)
        mgr = partial(mgr)
        mgr.class_scoped = True
        if weight is not None:
            mgr.weight = weight
        yield mgr


pony_fixtures.extend([
    use_ipdb_at_class_scope,
    use_ipdb,
])
