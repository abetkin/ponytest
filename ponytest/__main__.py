import sys

from .program import TestProgram
from .is_standalone import is_standalone_use

from .utils import PY2, drop_into_debugger

if PY2:
    from contextlib2 import ExitStack
else:
    from contextlib import ExitStack

with ExitStack() as stack:
    if '--debug' in sys.argv:
        stack.enter_context(drop_into_debugger())
    is_standalone_use(False)
    TestProgram(module=None)