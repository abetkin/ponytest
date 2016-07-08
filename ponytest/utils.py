import sys
import click

import abc

from functools import partial, wraps

PY2 = sys.version_info[0] == 2

@click.pass_context
def args_getter(ctx, *args, **kwargs):
    return ctx.params

def with_cli_args(func):
    '''
    A decorator helping with using click with standalone_mode turned off.
    '''
    getter_cmd = click.command(context_settings={
        'allow_extra_args': True,
        'ignore_unknown_options': True,
    })(args_getter)
    getter_cmd.params.extend(func.__click_params__)
    getter_cmd = partial(getter_cmd, standalone_mode=False)

    import ipdb; ipdb.set_trace()

    @wraps(func)
    def wrapper(*args, **kwargs):
        import ipdb
        with ipdb.launch_ipdb_on_exception():

            kwargs.update(
                getter_cmd()
            )
            return func(*args, **kwargs)
    return wrapper


class class_property(object):
    """
    Read-only class property
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        return self.func(cls)


def with_metaclass(meta, *bases):
    base_marker = [object]
    class __metaclass__(meta):
        def __new__(cls, name, this_bases, d):
            if this_bases is base_marker:
                return type.__new__(cls, name, tuple(this_bases), d)
            return meta(name, bases, d)
    return __metaclass__('<dummy_class>', base_marker, {})


class ContextManager(with_metaclass(abc.ABCMeta)):
    # Taken from Python 3.6 (contextlib).

    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        return None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is ContextManager:
            if (any("__enter__" in B.__dict__ for B in C.__mro__) and
                any("__exit__" in B.__dict__ for B in C.__mro__)):
                return True
        return NotImplemented