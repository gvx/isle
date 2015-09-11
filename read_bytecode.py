from functools import wraps
from .named import namedtuple
from .ast import *

@namedtuple
def Intermediate(kind, originalindex, value):
    assert kind in {'bytecode', 'if', 'for', 'do', 'label'}

def get_labels(bc):
    for i, b in enumerate(bc):
        if b[0].startswith('jump'):
            yield b[1]

def into_list(f):
    @wraps(f)
    def _f(*args, **kwargs):
        return list(f(*args, **kwargs))
    return _f

@into_list
def annotate_bytecode(bc):
    labels = set(get_labels(bc))
    for i, b in enumerate(bc):
        if i in labels:
            yield Intermediate('label', i, i)
        if b[0] == 'lambda':
            yield Intermediate('do', i, annotate_bytecode(b[1]))
        else:
            yield Intermediate('bytecode', i, b)

def for_nodes(abc):
    i = 0
    while i < len(abc):
        node = abc[i]
        if node.kind == 'bytecode' and node.value[0] == 'jump' and node.value[1] < node.originalindex:
            endi = i
            while not (abc[i].kind == 'label' and abc[i].originalindex == node.value[1]):
                i -= 1
                assert i >= 0
            abc[i + 1:endi + 1] = Intermediate('for', node.originalindex, abc[i + 4:endi]),
        elif node.kind == 'do':
            for_nodes(node.value)
        i += 1

def if_nodes(abc):
    i = len(abc) - 1
    while i >= 0:
        node = abc[i]
        if node.kind == 'bytecode' and node.value[0] == 'jump if nil':
            starti = i
            while not (abc[i].kind == 'label' and abc[i].originalindex == node.value[1]):
                i += 1
                assert i < len(abc)
            if abc[i - 1].kind == 'bytecode' and abc[i - 1].value[0] == 'jump': # else
                i2 = i
                while not (abc[i2].kind == 'label' and abc[i2].originalindex == abc[i - 1].value[1]):
                    i2 += 1
                    assert i2 <= len(abc), (i2, len(abc), abc)
                    if i2 == len(abc):
                        break
                abc[starti:i2] = Intermediate('if', node.originalindex, (abc[starti + 1:i - 1], abc[i + 1:i2])),
            else: # no else
                abc[starti:i] = Intermediate('if', node.originalindex, (abc[starti + 1:i], None)),
            i = starti
        elif node.kind in {'for', 'do'}:
            if_nodes(node.value)
        i -= 1

@into_list
def get_nodes(abc):
    i = 0
    while i < len(abc):
        node = abc[i]
        if node.kind == 'label':
            pass
        elif node.kind in {'for', 'do'}:
            yield Intermediate(node.kind, node.originalindex, get_nodes(node.value))
        elif node.kind == 'if':
            yield Intermediate(node.kind, node.originalindex, (get_nodes(node.value[0]), get_nodes(node.value[1])))
        else:
            yield node
        i += 1

@namedtuple
def Nodicle(name, value=None):
    pass

def make_intermediate_nodes(bc):
    abc = annotate_bytecode(bc)
    for_nodes(abc)
    if_nodes(abc)
    return get_nodes(abc)

def build_ast(nodes):
    build_stack = []
    for node in nodes:
        if node.kind == 'bytecode':
            c = node.value
            opc = c[0]
            if opc == 'lit':
                v = c[1]
                if v is None:
                    build_stack.append(Nil())
                elif isinstance(v, str):
                    build_stack.append(StrLit([RegFrag(v)]))
                elif isinstance(v, int):
                    build_stack.append(Int(v))
                elif isinstance(v, Symbol):
                    build_stack.append(Sym(v))
                else:
                    assert not 'reachable'
            elif opc == 'return':
                build_stack.append(ReturnValue(build_stack.pop()))
            elif opc == 'dup':
                build_stack.append(Nodicle(opc))
            elif opc == 'get name':
                build_stack.append(Name(c[1]))
            elif opc == 'get index':
                index = build_stack.pop()
                coll = build_stack.pop()
                build_stack.append(Index(coll, index))
            elif opc == 'get attr':
                build_stack.append(Attr(build_stack.pop(), c[1]))
            elif opc == 'get attr raw':
                build_stack.append(AttrGet(build_stack.pop(), c[1]))
            elif opc == 'new table':
                build_stack.append(TableLit([]))
            elif opc == 'set name':
                value = build_stack.pop()
                name = Name(c[1])
                if isinstance(value, Nodicle):
                    assert value.name == 'dup' and isinstance(build_stack[-1], UnOpS)
                else:
                    build_stack.append(Assign(name, '=', value))
            elif opc == 'set index':
                value = build_stack.pop()
                index = build_stack.pop()
                coll = build_stack.pop()
                if isinstance(coll, Nodicle) and coll.name == 'dup':
                    coll = build_stack[-1]
                    coll.value.append((index, value))
                else:
                    build_stack.append(Assign(Index(coll, index), '=', value))
            elif opc == 'set attr':
                value = build_stack.pop()
                coll = build_stack.pop()
                build_stack.append(Assign(Attr(coll, c[1]), '=', value))
            elif opc == 'set attr raw':
                value = build_stack.pop()
                coll = build_stack.pop()
                build_stack.append(Assign(AttrGet(coll, c[1]), '=', value))
            elif opc == 'call':
                func = build_stack.pop()
                arg = build_stack.pop()
                print(node.originalindex)
                build_stack.append(FuncCall(func, arg))
            elif opc == 'binop':
                right = build_stack.pop()
                left = build_stack.pop()
                build_stack.append(BinOp(left, c[1], right))
            elif opc == 'unop':
                right = build_stack.pop()
                op = c[1]
                build_stack.append((UnOpS if op in {'++', '--'} else UnOp)(op, right))
            elif opc == 'drop':
                pass
            elif opc == 'convert to string':
                build_stack.append(Nodicle(opc, build_stack.pop()))
            elif opc == 'collect string':
                m = build_stack.pop()
                c = []
                while not isinstance(m, Nil):
                    if isinstance(m, StrLit):
                        c.append(m[0][0])
                    elif isinstance(m, Nodicle) and m.name == 'convert to string':
                        c.append(m.value)
                    m = build_stack.pop()
                build_stack.append(StrLit(list(reversed(c))))
            else:
                assert not 'reachable', opc
        elif node.kind == 'do':
            build_stack.append(Do(build_ast(node.value)))
        elif node.kind == 'for':
            it = build_stack.pop()
            retval = build_stack.pop()
            assert isinstance(retval, Nil)
            # remove boilerplate
            del node.value[-6:]
            node.value.pop(0)
            # collect item names
            namelist = []
            while node.value[0].kind == 'bytecode' and node.value[0].value == ('dup',):
                namelist.append(node.value[2].value[1])
                del node.value[:3]
            # finally construct AST node
            build_stack.append(For(namelist, it, build_ast(node.value)))
        elif node.kind == 'if':
            cond = build_stack.pop()
            has_else = len(node.value[1]) > 1 or node.value[1][0].kind != 'bytecode' or node.value[1][0].value != ('lit', None)
            build_stack.append(If(cond, build_ast(node.value[0]), build_ast(node.value[1]) if has_else else None))
        else:
            assert not 'reachable'
    return build_stack

# build exps backwards
# then do tablelit forwards (check assigment to dup)
