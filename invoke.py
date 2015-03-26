from .named import namedtuple

import operator as _o
import reprlib
from functools import wraps
import traceback

__all__ = ['invoke']

class Nothing:
    def __repr__(self):
        return 'Nothing'
Nothing = Nothing()

class CallException(Exception):
    pass

def callfunc(func, arg, stack, callstack, allowvalue=False, tablesseen=None):
    if callable(func):
        ret = func(stack=stack, callstack=callstack, arg=arg)
        if ret is not Nothing:
            stack.append(ret)
    elif isinstance(func, Func):
        callstack.append(Scope(func, 0, arg))
    elif isinstance(func, Table) and S['()'] in func:
        if tablesseen is None:
            tablesseen = set()
        if func in tablesseen:
            raise Exception("recursive :'()' method")
        tablesseen.add(func)
        callfunc(func[S['()']], arg, stack, callstack, allowvalue=allowvalue, tablesseen=tablesseen)
    elif allowvalue:
        stack.append(func)
    else:
        raise CallException("cannot call a {} value".format('nil' if func is None else type(func)))

isle_keywords = { "if", "elsif", "else", "return", "end", "do", "for", "in" }

class ISLRepr(reprlib.Repr):
    def repr_Symbol(self, obj, level):
        import re
        if obj.value not in isle_keywords and re.match('^[a-zA-Z_][a-zA-Z_0-9]*$', obj.value):
            return ':' + obj.value
        else:
            return ":'{}'".format(obj.value)
    def repr_str(self, obj, level):
        return ''.join(self._repr_str(obj))
    def _repr_str(self, obj, escaped={'\n': 'n', '\t': 't', '"': '"', '\\': '\\', '\r': 'r'}):
        yield '"'
        for c in obj:
            if c in escaped:
                yield '\\'
                yield escaped[c]
            elif ord(c) < 32:
                yield '\\'
                yield hex(ord(c))[2:]
                yield ';'
            else:
                yield c
        yield '"'
    def repr_NoneType(self, obj, level):
        return 'nil'
    def repr_Func(self, obj, level):
        return 'do ... end'
    def repr_function(self, obj, level):
        name = obj.__name__
        return name[5:] if name.startswith('isle_') else name
    def repr_Table(self, obj, level):
        return ''.join(self._repr_dict(obj, level))
    def _repr_dict(self, obj, level):
        yield '('
        n = 1
        while n in obj:
            if n > 1:
                yield ', '
            yield self.repr1(obj[n], level - 1)
            n += 1
        kw_found = False
        for key, value in obj.items():
            if not isinstance(key, int) or not (1 <= key < n):
                if n > 1 or kw_found:
                    yield ', '
                kw_found = True
                if isinstance(key, Symbol):
                    yield self.repr1(key, level - 1)[1:]
                else:
                    yield '['
                    yield self.repr1(key, level - 1)
                    yield ']'
                yield '='
                yield self.repr1(value, level - 1)
        if n == 2 and not kw_found:
            yield ','
        yield ')'

class ISLStr(ISLRepr):
    def repr_str(self, obj, level):
        if level == self.maxlevel:
            return obj
        return super().repr_str(obj, level)

arepr = ISLRepr().repr
astr = ISLStr().repr

class Scope:
    def __init__(self, body, pc, env):
        self.body = body
        self.pc = pc
        assert(isinstance(env, Table))
        self.env = env
    def __hash__(self):
        return id(self)
    def __repr__(self):
        return 'Scope(body={body}, pc={pc}, env={env})'.format_map(self.__dict__)

@namedtuple
def Func(body, closure=()):
    # ensure Func is hashable
    hash(body)
    hash(closure)

class Symbol:
    __slots__ = ('value',)
    def __new__(cls, value):
        return S[value]
    def __repr__(self):
        return 'Symbol(value={!r})'.format(self.value)

class SType(dict):
    def __getattr__(self, item):
        return self[item]
    def __missing__(self, item):
        v = self[item] = object.__new__(Symbol)
        v.value = item
        return v

S = SType()

class Table(dict):
    def __hash__(self):
        return id(self)

# Symbol => sym
# str => str
# int => int
# Func/FunctionType => do .. end
# Table => table
# None => nil

def _wrapbool(f):
    @wraps(f)
    def _(*args, **kwargs):
        if f(*args, **kwargs):
            return S.t
        else:
            return None
    return _

def _and(left, right):
    if left is None:
        return left
    return right

def _or(left, right):
    if left is not None:
        return left
    return right

_binoptable = {'+': _o.add, '-': _o.sub, '*': _o.mul, '/': _o.floordiv, '%': _o.mod, '^': _o.pow,
    '==': _wrapbool(_o.eq), '!=': _wrapbool(_o.ne), '>': _wrapbool(_o.gt), '>=': _wrapbool(_o.ge),
    '<': _wrapbool(_o.lt), '<=': _wrapbool(_o.le), '&': _and, '|': _or}

_unoptable = {'!': _wrapbool(_o.not_), '+': _o.pos, '-': _o.neg, '++': lambda x: x + 1, '--': lambda x: x - 1}

def invoke(body, args):
    callstack = [Scope(body, 0, args)]
    stack = []
    try:
        while callstack:
            sc = callstack[-1]
            if sc.pc >= len(sc.body.body):
                callstack.pop()
                continue
            opcode, *opargs = sc.body.body[sc.pc]

            if opcode == 'lambda':
                stack.append(Func(body=opargs[0], closure=sc.body.closure + (sc.env,)))
            elif opcode == 'return':
                callstack.pop()
                continue
            elif opcode == 'jump':
                sc.pc = opargs[0]
                continue
            elif opcode == 'jump if nil':
                if stack.pop() is None:
                    sc.pc = opargs[0]
                    continue
            elif opcode == 'binop':
                right = stack.pop()
                left = stack.pop()
                if isinstance(left, dict):
                    s = S[opargs[0]]
                    if s in left:
                        callfunc(left[s], Table({1: right}), stack, callstack)
                    else:
                        raise Exception('used binop {} on table that doesn\'t support it'.format(opargs[0]))
                else:
                    stack.append(_binoptable[opargs[0]](left, right))
            elif opcode == 'unop':
                right = stack.pop()
                if isinstance(right, dict):
                    s = S[opargs[0]]
                    if s in right:
                        callfunc(right[s], Table(), stack, callstack)
                    else:
                        raise Exception('used unop {} on table that doesn\'t support it'.format(opargs[0]))
                else:
                    stack.append(_unoptable[opargs[0]](right))
            elif opcode == 'call':
                func = stack.pop()
                arg = stack.pop()
                callfunc(func, arg, stack, callstack)
            elif opcode == 'drop':
                stack.pop()
            elif opcode == 'dup':
                stack.append(stack[-1])
            elif opcode == 'swap':
                stack[-2:] = stack[:-3:-1]
            elif opcode == 'over':
                stack.append(stack[-2])
            elif opcode == 'rot':
                n = opargs[0]
                if n > 0:
                    stack.append(stack.pop(-n))
                else:
                    stack.insert(n, stack.pop())
            elif opcode == 'get index':
                key = stack.pop()
                coll = stack.pop()
                stack.append(coll.get(key))
            elif opcode == 'set index':
                value = stack.pop()
                key = stack.pop()
                coll = stack.pop()
                coll[key] = value
            elif opcode == 'get attr':
                coll = stack.pop()
                attr = opargs[0]
                value = coll.get(attr)
                callfunc(value, Table(), stack, callstack, allowvalue=True)
            elif opcode == 'set attr':
                value = stack.pop()
                coll = stack.pop()
                attr = opargs[0]
                try:
                    callstack.append(Scope(Func((('drop',),), ()), 0, Table()))
                    callfunc(coll.get(attr), Table({S.setter: S.t, 1: value}), stack, callstack)
                except CallException:
                    coll[attr] = value
                    callstack.pop()
            elif opcode == 'get attr raw':
                coll = stack.pop()
                attr = opargs[0]
                stack.append(coll.get(attr))
            elif opcode == 'set attr raw':
                value = stack.pop()
                coll = stack.pop()
                attr = opargs[0]
                coll[attr] = value
            elif opcode == 'get name':
                name = opargs[0]
                if isinstance(name, int) and name <= 0:
                    if name == 0:
                        stack.append(sc.body)
                    elif name == -1:
                        stack.append(sc.env)
                    else:
                        stack.append(sc.body.closure[name + 1])
                else:
                    if name in sc.env:
                        v = sc.env[name]
                    else:
                        for env in reversed(sc.body.closure):
                            if name in env:
                                v = env[name]
                                break
                        else:
                            v = None
                    stack.append(v)
            elif opcode == 'set name':
                value = stack.pop()
                name = opargs[0]
                if isinstance(name, int) and name <= 0:
                    raise Exception('cannot assign to $0 or $-n')
                for env in sc.body.closure:
                    if name in env:
                        env[name] = value
                        break
                else:
                    sc.env[name] = value
            elif opcode == 'new table':
                stack.append(Table())
            elif opcode == 'lit':
                stack.append(opargs[0])
            elif opcode == 'convert to string':
                stack.append(astr(stack.pop()))
            elif opcode == 'collect string':
                i = len(stack) - 1
                while stack[i] is not None:
                    i -= 1
                stack[i:] = [''.join(stack[i + 1:])]
            else:
                raise Exception('unknown opcode', opcode)
            sc.pc += 1
        return stack
    except Exception as e:
        traceback.print_exc()
        return None,
