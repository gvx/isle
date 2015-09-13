from .ast import *
from .invoke import S
from itertools import count

tagger = lambda x=count(): next(x)

def fixtags(t):
    return tuple(fixtags_(t))
def fixtags_(t):
    reg = {}
    i = 0
    for x in t:
        if x[0] == 'label':
            reg[x[1]] = i
        else:
            i += 1
    for x in t:
        fx = x[0]
        if fx in {'jump if nil', 'jump'}:
            yield fx, reg[x[1]]
        elif fx != 'label':
            yield x

def flattenbody(b, droplast=False):
    b = list(_flattenbody(b))
    if not droplast:
        if b[-1] == ('drop',): # return last expr
            b.pop()
    return b
def _flattenbody(b):
    statement = True
    for s in b:
        yield from s
        statement = isinstance(s, (Assign, ReturnValue))
        if not statement:
            yield ('drop',)
    if statement:
        yield from Nil()

@ReturnValue._method
def __iter__(self):
    yield from self.value
    yield ('return',)

@Assign._method
def __iter__(self):
    yield from self.name.assignto(self.value, binop=self.assign[:-1])

@For._method
def __iter__(self):
    start = tagger()
    end = tagger()
    yield from Nil()
    yield from self.iterable
    yield ('label', start)
    yield ('dup',)
    yield ('jump if nil', end)
    yield ('swap',)
    yield ('drop',)
    for i, name in enumerate(self.namelist, start=1):
        yield from Name(name).assignto([('dup',), ('get attr raw', i)])
    yield from flattenbody(self.body)
    yield ('swap',)
    yield ('dup',)
    yield ('get attr raw', S.arg)
    yield ('swap',)
    yield ('get attr raw', S.func)
    yield ('call',)
    yield ('jump', start)
    yield ('label', end)
    yield ('drop',)

@Do._method
def __iter__(self):
    yield ('lambda', fixtags(flattenbody(self.body)))

#@Class._method
#def __iter__(self):
#    yield from Do(self.body + [Name(-1)])

@If._method
def __iter__(self):
    yield from self.cond
    tag = tagger()
    yield ('jump if nil', tag)
    yield from flattenbody(self.thenbody)
    end = tagger()
    yield ('jump', end)
    yield ('label', tag)
    if self.elsebody is None:
        yield from Nil()
    else:
        yield from flattenbody(self.elsebody)
    yield ('label', end)

@BinOp._method
def __iter__(self):
    yield from self.left
    yield from self.right
    yield ('binop', self.op)

@UnOp._method
def __iter__(self):
    yield from self.right
    yield ('unop', self.op)

@UnOpS._method
def __iter__(self):
    yield from self.right.assignto(unops=self.op)

@FuncCall._method
def __iter__(self):
    yield from self.arg
    if isinstance(self.func, Attr):
        yield from AttrGet(coll=self.func.coll, attr=self.func.attr)
    else:
        yield from self.func
    yield ('call',)

@Index._method
def assignto(self, value=None, binop=None, unops=None):
    yield from self.coll
    yield from self.key
    if unops is not None:
        yield from UnOp(unops, [('over',), ('over',), ('get index',)])
        yield ('dup',)
        yield ('rot', -3)
    elif binop:
        yield from BinOp([('over',), ('over',), ('get index',)], binop, value)
    else:
        yield from value
    yield ('set index',)

@Index._method
def __iter__(self):
    yield from self.coll
    yield from self.key
    yield ('get index',)

@Attr._method
def assignto(self, value=None, binop=None, unops=None):
    yield from self.coll
    if unops is not None:
        yield from UnOp(unops, [('dup',), ('get attr', self.attr)])
        yield ('dup',)
        yield ('rot', -2)
    elif binop:
        yield from BinOp([('dup',), ('get attr', self.attr)], binop, value)
    else:
        yield from value
    yield ('set attr', self.attr)

@Attr._method
def __iter__(self):
    yield from self.coll
    yield ('get attr', self.attr)

@AttrGet._method
def assignto(self, value=None, binop=None, unops=None):
    yield from self.coll
    if unops is not None:
        yield from UnOp(unops, [('dup',), ('get attr raw', self.attr)])
        yield ('dup',)
        yield ('rot', -2)
    elif binop:
        yield from BinOp([('dup',), ('get attr raw', self.attr)], binop, value)
    else:
        yield from value
    yield ('set attr raw', self.attr)

@AttrGet._method
def __iter__(self):
    yield from self.coll
    yield ('get attr raw', self.attr)

@TableLit._method
def __iter__(self):
    yield ('new table',)
    for key, value in self.value:
        yield from Index(coll=[('dup',)], key=key).assignto(value)

@TableLit._method
def assignto(self, value=None, binop=None, unops=None):
    assert not (binop or unops) and self.value
    yield from value
    for i, (k, v) in enumerate(self.value):
        if i < len(self.value) - 1:
            yield ('dup',)
        yield from k
        if isinstance(v, Sym):
            v = Name(v.value)
        assert isinstance(v, (Name, TableLit)), "can only destructure into names and tables"
        yield from v.assignto([('get index',)])

@StrLit._method
def __iter__(self):
    if len(self.value) > 1:
        yield from Nil() # string terminator
        for v in self.value:
            if isinstance(v, RegFrag):
                if v.value:
                    yield ('lit', v.value)
            else:
                yield from v
                yield ('convert to string',)
        yield ('collect string',)
    else:
        yield ('lit', self.value[0].value)

@Sym._method
def __iter__(self):
    yield ('lit', self.value)

@Name._method
def __iter__(self):
    yield ('get name', self.value)

@Name._method
def assignto(self, value=None, binop=None, unops=None):
    if unops is not None:
        yield from UnOp(unops, [('get name', self.value)])
        yield ('dup',)
    elif binop:
        yield from BinOp([('get name', self.value)], binop, value)
    else:
        yield from value
    yield ('set name', self.value)

@Int._method
def __iter__(self):
    yield ('lit', self.value)

@Nil._method
def __iter__(self):
    yield ('lit', None)
