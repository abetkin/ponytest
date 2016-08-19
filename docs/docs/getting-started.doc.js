/* @flow */
/*
---
id: getting-started
title: Example
permalink: /docs/getting-started.html
next: new-project.html
---
*/

/*



Imagine we are testing a customer service. Say, a test expects a user with some customer plan,
and, possibly, some online payment service selected.
In the example below, the service is only available for the premium customer plan.

```python
from ponytest import provider

@provider(fixture='user')
@contextmanager
def get_user(test):
  user = User(name='John')
  user.save()
  test.user = user
  yield

@provider('premium', fixture='user_plan')
@contextmanager
def premium_plan():
  user.set_plan(UserPlan('premium'))
  yield

@provider('basic', fixture='user_plan')
@contextmanager
def basic_plan():
  user.set_plan(UserPlan('premium'))
  yield

@provider('paypal', fixture='payment_service')
@contextmanager
def paypal():
  user.set_payment_service(PayPal())
  yield

@provider('google_wallet', fixture='payment_service')
@contextmanager
def google_wallet():
  user.set_payment_service(GoogleWallet())
  yield


class Test(unittest.TestCase):
  pony_fixtures = {
    'test': ['user', 'user_plan', 'payment_service']
  }

  def test_service_1(self):
    with ExitStack() as stack:
      if self.user.plan.alias == 'basic':
        stack.enter_context(
          self.assertRaises(Exception, 'unavailable for given customer plan')
        )
      self.order_service_1()


```

*/
