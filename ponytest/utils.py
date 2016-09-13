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

    @wraps(func)
    def wrapper(*args, **kwargs):
        kwargs.update(
            getter_cmd(standalone_mode=False)
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

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


@add_metaclass(abc.ABCMeta)
class ContextManager(object):
    # Taken from Python 3.6 (contextlib).

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is ContextManager:
            if (any("__enter__" in B.__dict__ for B in C.__mro__) and
                any("__exit__" in B.__dict__ for B in C.__mro__)):
                return True
        return NotImplemented


class ValidationError(Exception):
    pass


def no_op(*args):
    pass


class merge_attrs(object):
    def __init__(self, *objects):
        self.objects = objects

    def __getattr__(self, key):
        for obj in self.objects:
            try:
                return getattr(obj, key)
            except AttributeError:
                pass
        raise AttributeError


class merge_dicts(object):
    def __init__(self, *objects):
        self.objects = objects

    def __getitem__(self, key):
        for obj in self.objects:
            try:
                return obj[key]
            except KeyError:
                pass
        raise KeyError

class drop_into_debugger(object):
    def __enter__(self):
        pass
    def __exit__(self, e, m, tb):
        if not e:
            return
        try:
            import ipdb as pdb
        except ImportError:
            import pdb
        import sys
        print(m.__repr__(), file=sys.stderr)
        pdb.post_mortem(tb)