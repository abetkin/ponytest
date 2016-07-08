
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


@with_cli_args(groups=['debug', 'debug2'])
@click.option('--ipdb', 'debug', is_flag=1)
@click.option('--ipdb', 'debug2', )
def use_ipdb(debug):
    import ipdb; ipdb.set_trace()
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


# TODO use nested list structure, make flat later ? weights!
# new_list = [1, rest, 2]
