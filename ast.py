from .named import namedtuple

@namedtuple
def ReturnValue(value):
    pass

def Return():
    return ReturnValue(Nil())

@namedtuple
def Assign(name, assign, value):
    pass

@namedtuple
def For(namelist, iterable, body):
    pass

@namedtuple
def Do(body):
    pass

#@namedtuple
#def Class(body):
#    pass

@namedtuple
def If(cond, thenbody, elsebody=None):
    pass

@namedtuple
def BinOp(left, op, right):
    pass

@namedtuple
def UnOp(op, right):
    pass

@namedtuple
def UnOpS(op, right):
    pass

@namedtuple
def FuncCall(func, arg):
    assert isinstance(arg, TableLit)

@namedtuple
def Index(coll, key):
    pass

@namedtuple
def Attr(coll, attr):
    pass

@namedtuple
def AttrGet(coll, attr):
    pass

@namedtuple
def TableLit(value):
    assert isinstance(value, list) #of (key, value)
    # (5, 6, 7, q=8, ["hi"]=9)
    # ==
    # TableLit([(Int(1), Int(5)), (Int(2), Int(6)), (Int(3), Int(7)), (Sym("q"), Int(8)), (StrLit([RegFrag("hi")]), Int(9))])

@namedtuple
def StrLit(value):
    assert isinstance(value, list) #of RegFrag and Exp

@namedtuple
def RegFrag(value):
    assert isinstance(value, str)

@namedtuple
def Sym(value):
    assert isinstance(value, str)

@namedtuple
def Name(value):
    assert isinstance(value, (str, int))

@namedtuple
def Int(value):
    assert isinstance(value, int)

@namedtuple
def Nil():
    pass
