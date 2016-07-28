'''
Usage:
python -m ponytest <unittest args> --- <OPTIONS>
'''

from .default_fixtures import debugger_support
from .main import pony_fixtures, provider, fixture_providers, TestCase
from .program import TestLoader, TestProgram
from .utils import with_cli_args, class_property, ValidationError, ContextManager


providers = fixture_providers