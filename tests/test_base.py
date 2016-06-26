
import click
from ponytest import Layer, with_cli_args

def ipdb_context(test):
    def decorate(func):
        import ipdb
        @wraps(func)
        def wrapper(*args, **kwds):
            raised = []
            with ipdb.launch_ipdb_on_exception():
                try:
                    return func(*args, **kwds)
                except Exception as exc:
                    raised.append(exc)
                    raise
            raise raised[0]
        return wrapper
    return decorate


class LoggingContext(Layer):

    def __init__(self, test):
        pass

    # def __enter__(self):
    #     print(1)

    # def __exit__(self, *exc_info):
    #     print(2)

    @classmethod
    def setUpClass(cls):
        print('setUp %s' % str(cls.__mro__))
        # TODO dict

    @classmethod
    @with_cli_args
    @click.option('--log', is_flag=True)
    def factory(cls, log):
        if log:
            yield cls


# class Layer(object):
#     TODO
#     def __init__(self, test):
#         1

#     def setUp(self):
#         1
#     def tearDown(self):
#         1
#     @classmethod
#     def setUpClass(cls):
#         1
#     @classmethod
#     def tearDownClass(cls):
#         1


# class DbContext(ContextDecorator):
#     def __iter__(self):
#         1

from contextlib import ContextDecorator, contextmanager

class TwoContexts(ContextDecorator):
    @classmethod
    def factory(cls):
        yield cls.one
        yield cls.two

    @classmethod
    @contextmanager
    def one(cls, test):
        print(test._testMethodName)
        try:
            import greenlet
            assert not hasattr(greenlet.getcurrent(), 'value')
            greenlet.getcurrent().value = 1
            yield
        finally:
            del greenlet.getcurrent().value

    @classmethod
    @contextmanager
    def two(cls, test):
        print(test._testMethodName)
        try:
            import greenlet
            assert not hasattr(greenlet.getcurrent(), 'value')
            greenlet.getcurrent().value = 2
            yield
        finally:
            del greenlet.getcurrent().value

from ponytest import default_layers

default_layers.extend(
    TwoContexts
)


from unittest import TestCase


class Test(TestCase):

    def test(self):
        import greenlet
        print( greenlet.getcurrent().value)
        self.assertTrue(0)
