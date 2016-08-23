

class DbFixture(Fixture):

    is_abstract = True
    fixture_key = 'db'

    def handler(self, providers, **kwargs):
        1

    def __enter__(self):
        1

    def __exit__(self, *info):
        1


class Sqlite(DbFixture):
    fixture_key = 'sqlite'
    enabled = True