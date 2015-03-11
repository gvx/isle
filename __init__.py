from .ast import *
from .visitor import *
from .invoke import *
from .stdlib import *
from .parse import *

def runfile(fname):
    invoke(Func(fixtags(flattenbody(parse(fname), droplast=True))), stdlib())
