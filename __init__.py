from .parse import *
from .visitor import *
from .invoke import *
from .stdlib import *

def runfile(fname):
    invoke(Func(fixtags(flattenbody(parse(fname), droplast=True))), stdlib())
