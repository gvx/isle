from .ast import *
from .invoke import arepr

# TODO:
# from bytecode to AST???

__all__ = ['ast_to_source']

BINOP_STRENGTH = {'|': 1, '&': 2, '+': 4, '-': 4, '*': 5, '/': 5, '%': 6, '^': 8}
UNOP_STRENGTH = 7

def binop_strength(op):
    if op in {'==', '!=', '<', '>', '>=', '<='}:
        return 3
    return BINOP_STRENGTH[op[0]]

def ast_to_source(t):
    return ''.join(to_source_body(t, 0, 0, end='', allowsingleline=False))

def to_source_body(body, indentation, strength, do=False, end='end', allowsingleline=True):
    if do:
        yield 'do'
    if len(body) < 2 and allowsingleline:
        if body:
            yield ' '
            yield from body[0].to_source(indentation, 0)
        yield ' '
        yield end
        return
    yield '\n'
    for line in body:
        yield '    ' * indentation
        yield from line.to_source(indentation + 1, 0)
        yield '\n'
    if end:
        yield '    ' * (indentation - 1)
        yield end

@ReturnValue._method
def to_source(self, indentation, strength):
    if isinstance(self.value, Nil):
        yield 'return'
    else:
        yield 'return '
        yield from self.value.to_source(indentation, 0)

@Assign._method
def to_source(self, indentation, strength):
    yield from self.name.to_source(indentation, strength)
    yield ' '
    yield self.assign
    yield ' '
    yield from self.value.to_source(indentation, strength)

@For._method
def to_source(self, indentation, strength):
    yield 'for'
    for i, name in enumerate(self.namelist):
        if i:
            yield ','
        yield ' '
        yield from Name(name).to_source(indentation, strength)
    if self.namelist:
        yield ' in'
    yield ' '
    yield from self.iterable.to_source(indentation, strength)
    yield from to_source_body(self.body, indentation, strength)

@Do._method
def to_source(self, indentation, strength):
    yield from to_source_body(self.body, indentation, strength, do=True)

@If._method
def to_source(self, indentation, strength):
    yield 'if '
    yield from self.cond.to_source(indentation, strength)
    elsif = self.elsebody and len(self.elsebody) == 1 and isinstance(self.elsebody[0], If)
    yield from to_source_body(self.thenbody, indentation, strength, end='els' if elsif else 'else' if self.elsebody else 'end')
    if elsif:
        yield from self.elsebody[0].to_source(indentation, strength)
    elif self.elsebody:
        yield from to_source_body(self.elsebody, indentation, strength)

@BinOp._method
def to_source(self, indentation, strength):
    s = binop_strength(self.op)
    if s < strength:
        yield '('
    parens = self.op[0] == '^' and isinstance(self.left, BinOp) and binop_strength(self.left.op) == s
    if parens:
        yield '('
    yield from self.left.to_source(indentation, s)
    if parens:
        yield ')'
    yield ' '
    yield self.op
    yield ' '
    parens = self.op[0] != '^' and isinstance(self.right, BinOp) and binop_strength(self.right.op) == s
    if parens:
        yield '('
    yield from self.right.to_source(indentation, s)
    if parens:
        yield ')'
    if s < strength:
        yield ')'

@UnOp._method
def to_source(self, indentation, strength):
    s = UNOP_STRENGTH
    if s < strength:
        yield '('
    yield self.op
    yield from self.right.to_source(indentation, s)
    if s < strength:
        yield ')'

@UnOpS._method
def to_source(self, indentation, strength):
    yield self.op
    yield from self.right.to_source(indentation, strength)

@FuncCall._method
def to_source(self, indentation, strength):
    func = self.func
    if isinstance(func, AttrGet):
        func = Attr(coll=func.coll, attr=func.attr)
    yield from func.to_source(indentation, strength)
    yield from self.arg.to_source(indentation, strength, True)

@Index._method
def to_source(self, indentation, strength):
    yield from self.coll.to_source(indentation, strength)
    yield '['
    yield from self.key.to_source(indentation, 0)
    yield ']'

@Attr._method
def to_source(self, indentation, strength):
    yield from self.coll.to_source(indentation, strength)
    yield '.'
    yield from Name(self.attr).to_source(indentation, strength)

@AttrGet._method
def to_source(self, indentation, strength):
    yield from self.coll.to_source(indentation, strength)
    yield '.@'
    yield from Name(self.attr).to_source(indentation, strength)

@TableLit._method
def to_source(self, indentation, strength, funcarg=False):
    yield '('
    i = 1
    nonintkey = False
    for key, value in self.value:
        if i > 1 or nonintkey:
            yield ', '
        if isinstance(key, Int) and key.value == i:
            i += 1
        else:
            nonintkey = True
            if isinstance(key, Sym):
                yield arepr(key.value)[1:]
            else:
                yield '['
                yield from key.to_source(indentation, 0)
                yield ']'
            yield '='
        yield from value.to_source(indentation, 0)
    if i == 2 and not nonintkey and not funcarg:
        yield ','
    yield ')'

@StrLit._method
def to_source(self, indentation, strength):
    yield '"'
    for v in self.value:
        if isinstance(v, RegFrag):
            yield arepr(v.value)[1:-1]
        else:
            yield '{'
            yield from v.to_source(indentation, 0)
            yield '}'
    yield '"'

@Sym._method
def to_source(self, indentation, strength):
    yield arepr(self.value)

@Name._method
def to_source(self, indentation, strength):
    if isinstance(self.value, int):
        yield '$'
        yield str(self.value)
    else:
        yield arepr(self.value)[1:]

@Int._method
def to_source(self, indentation, strength):
    yield str(self.value)

@Nil._method
def to_source(self, indentation, strength):
    yield 'nil'
