from .invoke import astr, arepr, Func, Table, Scope, Nothing, callfunc, S
from .visitor import fixtags, flattenbody
from .parse import parseFile
from .serialize import serialize

def isle_serialize(stack, callstack, arg):
    return serialize(arg[1])

def isle_apply(stack, callstack, arg):
    assert isinstance(arg[2], Table)
    callfunc(arg[1], arg[2], stack, callstack)
    return Nothing

def isle_puts(stack, callstack, arg):
    n = 1
    while n in arg:
        print(astr(arg[n]))
        n += 1

def isle_show(stack, callstack, arg):
    print(', '.join(arepr(x) for x in _iter_args(arg)))

def isle_assert(stack, callstack, arg):
    assert arg[1] is not None

def isle_assert_error(stack, callstack, arg):
    callstack.append(Scope(arg[1], 0, Table()))
    #something something error handling

def isle_replace_closure(stack, callstack, arg):
    assert(isinstance(arg[1], Func))
    assert(isinstance(arg[2], Table))
    new_closure = tuple(_iter_args(arg[2]))
    for env in new_closure:
        assert(isinstance(env, Table))
    return Func(body=arg[1].body, closure=new_closure)

def _iter_args(t):
    n = 1
    while n in t:
        yield t[n]
        n += 1

def next_item(stack, callstack, arg):
    try:
        return Table({S.func: next_item, 1: arg[1](stack, callstack, arg), S.arg: Table([(1, arg[1])])})
    except StopIteration:
        return None

def isle_args(stack, callstack, arg):
    it = _iter_args(arg[1])
    return next_item(stack, callstack, arg={1:lambda s,c,a:next(it)})

def isle_chars(stack, callstack, arg):
    assert isinstance(arg[1], str)
    it = iter(arg[1])
    return next_item(stack, callstack, arg={1:lambda s,c,a:next(it)})

def isle_range(stack, callstack, arg):
    start = arg[S.start] if S.start in arg else arg[1] if 2 in arg else 1
    stop = arg[S.stop] if S.stop in arg else arg[2] if 2 in arg else arg[1]
    step = arg.get(S.step, 1)
    if start <= stop:
        return Table({S.func: isle_range, 1: start, S.arg: Table({S.start: start + step, S.step: step, S.stop: stop})})

def isle_require(stack, callstack, arg):
    env = Table()
    useenv = arg.get(S.useret) is None
    callstack.append(Scope(Func(fixtags(flattenbody(parseFile(arg[1]), droplast=useenv)), ()), 0, env))
    return env if useenv else Nothing

def isle_slice(stack, callstack, arg):
    string = arg[1]
    start = arg[2]
    if start < 0:
        start = len(string) + start + 1
    end = arg.get(3, start)
    if end < 0:
        end = len(string) + end + 1
    assert 1 <= start <= len(string)
    assert start <= end <= len(string)
    return string[start - 1:end]

def isle_delkey(stack, callstack, arg):
    table = arg[1]
    key = arg[2]
    if key in table:
        del table[key]

def stdlib():
    lib = Table()
    for key, value in globals().items():
        if key.startswith('isle_'):
            lib[S[key[5:]]] = value
    return lib

stdlib = stdlib()
