from .program import TestProgram
from .is_standalone import is_standalone_use

is_standalone_use(False)
import ipdb
with ipdb.launch_ipdb_on_exception():

    TestProgram(module=None)