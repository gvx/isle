from . import *

import readline

ps1 = '\n% '
ps2 = '| '
try:
    from blessings import Terminal
    term = Terminal()
    ps1 = term.bold_blue(ps1)
    ps2 = term.bold_blue(ps2)
    def fancy_movement():
        print(term.move_up() + term.clear_eol() + term.move_up())
except ImportError:
    def fancy_movement():
        pass

def getfilefunc(mod, droplast=True):
    return Func(tuple(fixtags(flattenbody(mod, droplast=droplast))))

def runfile(fname):
    invoke(getfilefunc(parseFile(fname)), stdlib())

def readProgram():
    try:
        yield input(ps1)
        while True:
            line = input(ps2)
            if not line:
                fancy_movement()
                return
            yield line
    except EOFError:
        print()
        raise SystemExit

def interactive():
    env = stdlib()
    while True:
        try:
            retval, = invoke(getfilefunc(parseString('\n'.join(readProgram())), droplast=False), env)
            if retval is not None:
                print(arepr(retval))
        except KeyboardInterrupt:
            print()
        except Exception as e:
            print(e)

import sys
if len(sys.argv) > 1:
    runfile(sys.argv[1])
else:
    interactive()
