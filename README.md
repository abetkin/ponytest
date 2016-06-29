# ponytest

## What it is

Testing utility used to test [Pony ORM](https://github.com/ponyorm/pony).
A drop-in `unittest` replacement.

## Motivation

This piece of code was written because none of testing frameworks provided a clear way to launch the same tests with
different setup / teardown fixtures. Specifically,
we needed a way to run the same set of tests against different databases.

```
python -m test.utility tests --db mysql --db oracle
```

## Features

With ponytest, you can:

- drop into debugger on failures, including errors in methods like `setUp` and `tearDownClass`
- launch the same set of tests with different setup / teardown fixtures
- define test fixtures with context managers, and register them globally

Ponytest is lightweight (< 200 SLOC)

## Try it

You can install ponytest with

```
python -m pip install git+https://github.com/abetkin/ponytest
```

Debugger mode:

```
python -m ponytest <unittest args> -- --ipdb
```

Ponytest lets you define fixtures with contextmanagers. Fixtures can be either test-scoped (wrapping a test) or case-scoped
(wrapping a set of tests in a testcase class). Case-scoped is default.

```python
from contextlib import contextmanager

@contextmanager
def fixture(cls):
    print('setting up', cls)
    cls.initialized = True
    yield
    print('tearing down', cls)

fixture.test_scoped = False # default

import unittest

class MyTest(unittest.TestCase):

    pony_contexts = [
        [fixture]
    ]

    def test(self):
        self.assertIn('initialized', self.__class__)
```

As you see, we defined our fixture with a list (`[fixture]`). That's because there could be multiple of them. In that case,
the test would be run with every combination of fixtures. For, example, for the fixture set below

```python
pony_contexts = [
    [fixt1],
    [fixt2, fixt3]
]
```

we would have `test` run 2 times, first with `[fixt1, fixt2]` and second with `[fixt1, fixt3]` contexts.

Besides a list, a fixture can be specified with a callable that returns iterable
(in case when, say, fixture set depends on the command line arguments passed):

```python
import click # http://click.pocoo.org/
from ponytest import with_cli_args

@with_cli_args
@click.option('--ipdb', 'debug', is_flag=True)
def use_ipdb(debug):
    if debug:
        yield ipdb_context
```

You can also register fixtures globally (like it is done with the `ipdb` fixture):

```python
from ponytest import pony_contexts # a deque
pony_contexts.appendleft(a_fixture)
```

You can find more examples in [tests](https://github.com/abetkin/ponytest/tree/master/tests)
and [default_contexts.py](https://github.com/abetkin/ponytest/blob/master/ponytest/default_contexts.py) module.

## How it works

As you probably presumed, `unittest` is not designed to be extended. Ponytest therefore (almost)
doesn't mess with the testing machinery of `unittest`. It overrides single
`loadTestsFromTestCase` method of the test loader, creating a subclass of the testcase passed,
that wraps test methods of the parent:

```python
class PONY_MyTest(MyTest):

    @classmethod
    @wrapping.with.fixtures
    def setUpClass(cls):
        '...'

    @wrapping.with.fixtures
    def tearDown(self):
        '...'

    @wrapping.with.fixtures
    def test(self):
        '...'
```

`Note:` Of course, regular test methods and the ones like `setUp` and `setUpClass` are wrapped differently.