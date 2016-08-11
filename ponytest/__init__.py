'''
Usage:
python -m ponytest <unittest args> --- <OPTIONS>
'''

from . import  default_handlers
from .default_fixtures import debugger_support
from .main import pony_fixtures, TestCase, Fixture
from .config import fixture_providers, provider_validators
from .program import TestLoader, TestProgram
from .utils import with_cli_args, class_property, ValidationError, ContextManager


providers = fixture_providers