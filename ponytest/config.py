

# fixture_providers = {}
# fixture_handlers = {}
# provider_validators = {}

# pony_fixtures = {
#     'test': ['ipdb'], 'class': ['ipdb']
# }

class config(object):

    class case_fixtures:
        ALL = ['ipdb']

    class class_fixtures:
        ALL = ['ipdb']

    def merge(self, other):
        1