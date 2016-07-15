

# class Fixt(ContextDecorator): # custom


#     def __enter__(self):
#         1
    
#     @class_property
#     def enabled(cls): # by default
#         1
    
#     @class_property
#     def variants(cls):
#         ...


class Test(unittest.TestCase):

    fixture_variants = {
        'init_db': ['postgresql']
    }


# fixture vs. variant


@fi_list.register_fixt('fi', 'variant')
class Variant(object):
    # KEY = 'common'
    # VARIANT = 'postgresql'
    
    def validate(fixture_chain, klass):
        return fixture_chain

    


@fi_list.register_fixt('fi')
class Variant(object):

    order = 1

    @class_property
    def variants(cls):
        1
    
    @class_property
    def enabled(cls):
        1

@fi_list.register_fixt('fi')
def F(Test):
    def wrapper(func):
        return func
    return wrapper

F.variants = ['key1', 'key2']



class T:

    def test(self):
        db = self.fixtures['init_db']
        # Test.fixtures

