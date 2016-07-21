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

## Writing fixtures

Test fixture can be either a context managers
(with `__enter__` and `__exit__` methods doing setup and teardown)
or a callable-wrapper (`new_test = fixture(test)`). Both can be either test-scoped (wrapping a single test)
or class-scoped (wrapping a testsuite formed from a testcase class). Default is test-scoped.
Use `fixture.class_scoped = True` to change that.

Let's see some examples.

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
        ('myfixture', [fixture]),
    ]

    def test(self):
        self.assertTrue(self.initialized)
```

As you see, we defined our fixture with a list (`[fixture]`). That's because there can be multiple of them. For example, this will execute `test` twice:

```python
pony_fixtures = [
    ('myfixture', [fixture, fixture])
]
```

Also, you probably noticed that `pony_fixtures` is a list of tuples.
It could be anything we can pass to `OrderedDict` constructor, even a dict
(of course, the fixtures order is not guaranteed in that case):

```python
pony_fixtures = {'myfixture': [fixture, fixture]}
```

Also notice the `'myfixture'` key, that is not used in this simple example.
You are required to always provide the fixture key, for consistency.

Of course, in a real case one would want to specify different fixtures in that list. It will cause the test to be run
with every combination of fixtures. For, example, for the fixture set below

```python
pony_fixtures = enumerate([
    [fixt1],
    [fixt2, fixt3],
])
```

we will have `test` run 2 times, first with `[fixt1, fixt2]` and second with `[fixt1, fixt3]` fixtures.

Notice the `enumerate` function, that provided fixtures with integer keys, since we are not interested with them.

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
pony_fixtures = {'ipdb': use_ipdb}
```

Fixture can define `fixture_name` attribute. If it does, that name will make part of the test class name:

```
======================================================================
ERROR: tearDownClass (my.test.Case_with_myfixture)
----------------------------------------------------------------------
```

In the example above the value of `fixture_name` was set to `"myfixture"`.

## Registering fixtures globally

You can also register fixtures globally (like it is done with the `ipdb` fixture):

```python
from ponytest import pony_fixtures # OrderedDict
pony_fixtures.update({'ipdb': use_ipdb})
```

Note that the "ipdb" fixture was added to the end of the `OrderedDict`,
so that to keep all contexts available in the debug session.

Ponytest will look for declared `pony_fixtures` attribute in the test class, otherwise will use `ponytest.pony_fixtures`.
You surely can extend the fixture set for a testcase:

```python
from ponytest import pony_fixtures
from copy import copy

class MyTest(unittest.TestCase):
    pony_fixtures = copy(pony_fixtures)
    pony_fixtures.update(extra_fixtures)
```

There is a shortcut for this:

```python
class MyTest(unittest.TestCase):
    update_fixtures = extra_fixtures
```

## Registering fixture providers

TODO document it

## `exclude_fixtures`, `test_scoped`, `class_scoped` attributes

TODO document it

## Lazy fixtures

TODO document it

## Examples

You can find more examples in [tests](https://github.com/abetkin/ponytest/tree/master/tests)
and [default_fixtures.py](https://github.com/abetkin/ponytest/blob/master/ponytest/default_fixtures.py) module.

## How it works

As you probably presumed, `unittest` is not designed to be extended. Ponytest therefore (almost)
doesn't mess with the testing machinery of `unittest`. It overrides
`loadTestsFromTestCase` method of the test loader (actually, also `loadTestsFromName` for consistency), creating a subclass of the testcase passed,
that wraps test methods of the parent.

```python
class PONY_MyTest(MyTest):

    @wrapping_with_fixtures
    def test(self):
        ...
```

TODO document it better