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

Also, it is considered in some dev circles that missing debugger support in unittest makes it unusable.

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

`Note:` You can pass additional arguments for ponytest after the double-dash separator (`--`)

Ponytest lets you define fixtures with contextmanagers. Fixtures can be either test-scoped (wrapping a single test)
or class-scoped (wrapping all tests in a testcase class). Default is test-scoped.
Use `fixture.class_scoped = True` to change that.

```python
from contextlib import contextmanager

@contextmanager
def fixture(test):
    print('setting up', test._testMethodName)
    test.initialized = True
    yield
    print('tearing down', test._testMethodName)

fixture.class_scoped = False # could omit this

import unittest

class MyTest(unittest.TestCase):

    pony_fixtures = [
        [fixture]
    ]

    def test(self):
        self.assertTrue(self.initialized)
```

As you see, we defined our fixture with a list (`[fixture]`). That's because there can be multiple of them. For example, this will execute `test` twice:

```python
pony_fixtures = [
    [fixture, fixture]
]
```

Of course, in a real case one would want to specify different fixtures in that list. It will cause the test to be run
with every combination of fixtures. For, example, for the fixture set below

```python
pony_fixtures = [
    [fixt1],
    [fixt2, fixt3],
]
```

we will have `test` run 2 times, first with `[fixt1, fixt2]` and second with `[fixt1, fixt3]` fixtures.

Besides a list, a fixture can be specified with a callable that returns iterable
(in case when, say, fixture set depends on the command line arguments passed):

```python
import click # http://click.pocoo.org/
from ponytest import with_cli_args

@with_cli_args
@click.option('--ipdb', 'debug', is_flag=True)
def use_ipdb(debug):
    if debug:
        yield ipdb_fixture

# And later
pony_fixtures = [
    use_ipdb
]
```

Fixture can define `fixture_name` attribute. If it does, that name will make part of the test class name:

```
======================================================================
ERROR: tearDownClass (my.test.Case_with_myfixture)
----------------------------------------------------------------------
```

In the example above the value of `fixture_name` was set to `"myfixture"`.

You can also register fixtures globally (like it is done with the `ipdb` fixture):

```python
from ponytest import pony_fixtures # a deque
pony_fixtures.appendleft(use_ipdb)
```

Note that `use_ipdb` was appended to the left of the deque, which will let you debug your own fixtures.

Ponytest will look for declared `pony_fixtures` attribute in the test class, otherwise will use `ponytest.pony_fixtures`.
You surely can extend the fixture set for a testcase:

```python
class MyTest(unittest.TestCase):
    from ponytest import pony_fixtures
    pony_fixtures.extend(extra_fixtures)
```

You can find more examples in [tests](https://github.com/abetkin/ponytest/tree/master/tests)
and [default_fixtures.py](https://github.com/abetkin/ponytest/blob/master/ponytest/default_fixtures.py) module.

## How it works

As you probably presumed, `unittest` is not designed to be extended. Ponytest therefore (almost)
doesn't mess with the testing machinery of `unittest`. It overrides single
`loadTestsFromTestCase` method of the test loader, creating a subclass of the testcase passed,
that wraps test methods of the parent:

```python
class PONY_MyTest(MyTest):

    @classmethod
    @wrapping_with_fixtures
    def setUpClass(cls):
        ...

    @wrapping_with_fixtures
    def tearDown(self):
        ...

    @wrapping_with_fixtures
    def test(self):
        ...
```

`Note:` Of course, regular test methods and the ones like `setUp` and `setUpClass` are wrapped differently.
