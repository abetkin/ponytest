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


class BoundMethod(object):
    '''
    Bound method of class or object, depending on how it's called
    '''
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func.__get__(instance or owner)

def no_op(*args):
    pass