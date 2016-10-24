**loader**

package-level fixture list

```python
load_tests = FixtureLoader(['db', 'init'])
```

**use of fixtures in tests**

Besides setup-teardown functions, fixtures provide context to tests via attributes.

```python
@contextmanager
def myfixture(test):
  yield {'my_resource': SomeResource()}
```

The dictionary returned in fixture's `__enter__` method will be added to test class namespace.

**parameters**

The most common way should be defining parametrized fixture through inheritance:

```python
class DbContext(Fixture):
  __key__ = 'db'
  
class PostgresqlContext(DbContext):
  pass

class ExcludeThis(DbContext):
  is_fixture = False
```

**use of tests in fixtures**

```python
class MyFixture(Fixture):

  def __enter__(self, test):
    # `test`: probably, it should be not real test or test class instance but helper obj
    if should_skip(test):
       raise SkipFixture
```
