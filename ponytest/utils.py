import sys
import click

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

    @wraps(func)
    def wrapper(*args, **kwargs):
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