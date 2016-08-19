/* @flow */
/*
---
layout: home
title: Unittest is usable now
id: home
bodyClass: home
---
*/

/*

<header class='main hero'><div class='width'>
  <h1><i>ponytest</i></h1>
  <div>
    <p>unittest is usable now</p>
  </div>
</div></header>

<section class="marketing-row three"><div class="width">
<div class="col first" markdown="1">

## Fixtures via context managers

Ponytest recommends to define setup/teardown actions for a test using python context managers.
While writing methods like `setUp` and `setUpClass` also works, the former allows you to structure fixtures into lists.

</div>
<div class="col" markdown="1">

## Parameterize tests with fixture providers

Allows tests to be parametrized in such a way, that the same tests to be executed in different contexts, i.e. with
different setup/teardown fixtures.

</div>
<div class="col" markdown="1">

## Command line integration

Every fixture can be toggled (or specified the providers list) from the command line. Btw, an example
of that is
`--ipdb` flag that toggles debugging on test failures.

</div>
</div></section>

<section class='content'><div class='width'>
<article markdown="1">


Let's see the use of context managers in ponytest. Let's craft a simple logging fixture.

```python
from contextlib import contextmanager
from ponytest import provider, pony_fixtures

@provider(fixture='log', enabled=False)
@contextmanager
def log(test):
    level = logging.getLogger().level
    logging.getLogger().setLevel(logging.INFO)
    yield
    logging.getLogger().setLevel(level)

pony_fixtures['test'].append('log')
```

Fixture itself is a singleton (a class that inherits from `Fixture`, that was created automatically
with `'log'` as its key). What we define with a context manager is a fixture provider.

Than we register fixture globally updating `pony_fixtures['test']`, which means test-scoped fixtures.
So it will wrap every test.  If we placed it in `pony_fixtures['class']`, it would execute once for every
testcase class.

We did not enable logging fixture provider by default, so it will be used only when it's command line option
will be passed, like this:

```bash
$ python -m ponytest tests.test_me -- --log
```

`--` separates unittest arguments and ponytest options. Since `'log'` fixture is registered globally,
we will have every test use it.

The next example demonstrates the use of providers.


Suppose we ship 2 implementation of calculators, one of which will be used, depending on the user config.
we want to check that both implementation pass a set of tests.

```python
class ReduceAddCalculator(object):
    def eval(self, expr):
        items = [float(i) for i in expr.split('+')]
        return reduce(op.add, items)

class PythonEvalCalculator(object):
    def eval(self, expr):
        return eval(expr)
```

As you probably guessed, the first calculator will work only for addition. Let's write the providers.

```python
from functools import reduce
import operator as op

@provider('reduce add', fixture='calculator')
class ReduceAdd(object):
    def __init__(self, test):
        test.calculator = ReduceAddCalculator()

    __enter__ = __exit__ = lambda *args: None


@provider('python exec', fixture='calculator')
class PythonExec(object):
    def __init__(self, test):
        test.calculator = PythonEvalCalculator()
    
    __enter__ = __exit__ = lambda *args: None


class TestCalculator(unittest.TestCase):
    include_fixtures = {
        'test': ['calculator']
    }

    def test_add(self):
        self.assertEqual(self.calculator.eval('1+1'), 2)
    
    def test_sub(self):
        self.assertEqual(self.calculator.eval('1-1'), 0)

```

Now we did not add the `'calculator'` fixture to the global list, but specified it in the testcase.
We could use the `pony_fixtures` attribute as well. With `include_fixtures`, you can specify adiitional fixtures,
that will be appended to the global ones.

Let's run the test:

``` bash
$ python3 -m ponytest test_calc
.E..
======================================================================
ERROR: test_sub (test_calc.TestCalculator) [reduce add]
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/vitalik/projects/ponytest/ponytest/main.py", line 180, in wrapper
    _test_func(test)
  File "/home/vitalik/Documents/test_calc.py", line 48, in test_sub
    self.assertEqual(self.calculator.eval('1-1'), 0)
  File "/home/vitalik/Documents/test_calc.py", line 20, in eval
    items = [float(i) for i in expr.split('+')]
  File "/home/vitalik/Documents/test_calc.py", line 20, in <listcomp>
    items = [float(i) for i in expr.split('+')]
ValueError: could not convert string to float: '1-1'
----------------------------------------------------------------------
Ran 4 tests in 0.004s

FAILED (errors=1)
```

As you can see, 4 tests were run, 1 of which failed with the "reduce add" provider.

Read more in the [docs](/docs) or go to [repository](https://github.com/abetkin/ponytest).



</article>
</div></section>


*/
