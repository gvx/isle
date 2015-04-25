from . import ast
from .invoke import S, Symbol, isle_keywords
from pyparsing import *

__all__ = ['parseFile', 'parseString']

ParserElement.setDefaultWhitespaceChars(' \t\r')
NameExp = Forward()
Exp = Forward()

NumLit = Word(nums + '-', nums).setParseAction(lambda t: ast.Int(int(t[0])))

def rejectKeywords(string,loc,tokens):
    if tokens[0] in isle_keywords:
        raise ParseException(string,loc,"found keyword %s" % tokens[0])
def nameParseAction(string,loc,tokens):
    if isinstance(tokens[0], str):
        tokens[0] = Symbol(tokens[0])
    return ast.Name(tokens[0])

SymName = Word(srange('[a-zA-Z_]'), srange('[a-zA-Z_0-9]')).setParseAction( rejectKeywords ) | (Suppress("'") + CharsNotIn("'") + Suppress("'"))
Name = SymName | ('$' + NumLit).setParseAction(lambda t: t[1].value)
Name.setParseAction(nameParseAction)

Assigner = Regex(r'(?:[&|!%<=>+*/\^-]*[&|!%<>+*/\^-])?=')
Assign = NameExp + Assigner + Exp
Assign.setParseAction(lambda t: ast.Assign(t[0], t[1], t[2]))

Return = Keyword("return") + Optional(Exp)
Return.setParseAction(lambda t: ast.ReturnValue(t[1]) if len(t) == 2 else ast.Return())
Stmt = Assign | Return | Exp

NewLine = Regex(r'[\n;]')
NL = Suppress(OneOrMore(NewLine))
OptNL = Optional(NL)

Stmts = Optional(delimitedList(OptNL + (Optional(Stmt) + Suppress("#" + restOfLine) | Stmt), NewLine))
Program = Stmts + OptNL
FuncDef = Suppress(Keyword("do")) + Program + Suppress(Keyword("end"))
FuncDef.setParseAction(lambda t: ast.Do(t.asList()))

Body = Stmts + OptNL
Body.setParseAction(lambda t: [t.asList()])

ForLoop = Suppress(Keyword("for")) + (delimitedList(Name).setParseAction(lambda t:[[x.value for x in t.asList()]]) + Suppress(Keyword("in")) | Empty().setParseAction(lambda t: [[]])) + Exp + Body + Suppress(Keyword("end"))
ForLoop.setParseAction(lambda t: ast.For(t[0], t[1], t[2]))

IfExp = Keyword("if") + Exp + Body + ZeroOrMore(Keyword("elsif") + Exp + Body) + Optional(Keyword("else") + Body) + Keyword('end')
def if_parse(t):
    return parse_if(t.asList())
def parse_if(l):
    if l[0] == 'else':
        return l[1]
    elif l[0] == 'end':
        return
    return [ast.If(l[1], l[2], parse_if(l[3:]))]
IfExp.setParseAction(if_parse)

NameOrIndex = Name.copy().setParseAction(lambda s,l,t: (nameParseAction(s,l,t), ast.Sym(t[0]) if isinstance(t[0], Symbol) else ast.Int(t[0]))[1]) | Suppress("[") + Exp + Suppress("]")

def _makeflag(s):
    return [s, "=", s]
FlagParam = (SymName + "=" + ~Regex(r"[&|%<=>*/\^]")).setParseAction(lambda s,l,t: _makeflag(ast.Sym(Symbol(t[0]))))
TableLitOrParens = Suppress("(") + Optional(delimitedList((Optional(NameOrIndex + "=" + ~Regex(r"[&|%<=>*/\^]")) + Exp | FlagParam), ",") + Optional(",")) + Suppress(")")
def makeTable(tokens):
    v = []
    n = 1
    while tokens:
        keyorvalue = tokens.pop(0)
        if keyorvalue == ',':
            break
        if tokens:
            nextkeyvalue = tokens.pop(0)
            if nextkeyvalue == '=':
                v.append((keyorvalue, tokens.pop(0)))
                continue
            elif nextkeyvalue != ',':
                tokens.insert(0, nextkeyvalue)
        v.append((ast.Int(n), keyorvalue))
        n += 1

    return ast.TableLit(v)

def maybeMakeTable(tokens):
    if len(tokens) == 1: return tokens[0]
    return makeTable(tokens)

TableLitOrParens.setParseAction(maybeMakeTable)
TableLit = TableLitOrParens.copy().setParseAction(makeTable)

escape_chars = {'\\n': '\n', '\\r': '\r', '\\t': '\t'}

Special = (Regex(r'\\[\\"{}nrt]').setParseAction(lambda t: ast.RegFrag(escape_chars.get(t[0], t[0][1])))
    | Regex(r"\\[0-9a-fA-F]{1,6};").setParseAction(lambda t: ast.RegFrag(chr(int(t[0][1:-1], 16))))
    | Suppress("{") + Exp + Suppress("}"))

#SpecialNL = Special #r"\\[\\"{}nrt]" | r"\\[0-9a-fA-F]{1,6};" | "{" + Optional("\n") + Stmts + Optional("\n") + "}"

HereDoc = Regex(r"<<<([^\n]*)\n(?P<text>(?:[^\n]*\n)*?)\1>>>").setParseAction(lambda t: ast.RegFrag(t['text']))

StrContent = Regex(r'[^{}"\n\\]*').setParseAction(lambda t: ast.RegFrag(t[0]))
StrContentNL = Regex(r'[^{}"\\]*').setParseAction(lambda t: ast.RegFrag(t[0]))

StrLit = (Suppress('"""') + StrContentNL + ZeroOrMore(Special + StrContentNL) + Suppress('"""')
    | Suppress('"') + StrContent + ZeroOrMore(Special + StrContent) + Suppress('"')
    | HereDoc).setParseAction(lambda t: ast.StrLit(t.asList()))

SymLit = (":" + Name).setParseAction(lambda t: ast.Sym(t[1].value))

Nil = Keyword("nil").setParseAction(lambda t: ast.Nil())

TermExp =  (Nil | SymLit | StrLit | NumLit | TableLitOrParens | FuncDef | ForLoop | IfExp | Name)
NameExp << (TermExp + ZeroOrMore("[" + Exp + Suppress("]") | "." + Name | ".@" + Name | TableLit))
nameexpast = {'[': ast.Index, '.': ast.Attr, '.@': ast.AttrGet}
def parsenameexp(t):
    i = 1
    temp = t[0]
    while i < len(t):
        if isinstance(t[i], str):
            if t[i].startswith('.'):
                t[i + 1] = t[i + 1].value
            temp = nameexpast[t[i]](temp, t[i + 1])
            i += 2
        else:
            if not isinstance(t[i], ast.TableLit):
                t[i] = ast.TableLit([(ast.Int(1), t[i])])
            temp = ast.FuncCall(temp, t[i])
            i += 1
    return temp
NameExp.setParseAction(parsenameexp)
def binopparse_l(t):
    l = t.asList()
    i = 1
    temp = l[0]
    while i < len(l):
        temp = ast.BinOp(temp, t[i], t[i + 1])
        i += 2
    return temp

def binopparse_r(t):
    l = t.asList()
    i = len(l) - 2
    temp = l[-1]
    while i > 0:
        temp = ast.BinOp(t[i - 1], t[i], temp)
        i -= 2
    return temp

def unopparse(t):
    l = t.asList()
    temp = l[-1]
    for v in reversed(l[:-1]):
        temp = (ast.UnOpS if v in {'++', '--'} else ast.UnOp)(v, temp)
    return temp

PowExp = (NameExp + ZeroOrMore((Regex(r'\^[&|!%<=>+*/\^-]*[&|!%<>+*/\^-]') | Literal("^")) + NameExp)).setParseAction(binopparse_r)
UnOpExp = (ZeroOrMore(oneOf("! + - ++ --")) + PowExp).setParseAction(unopparse)
MulExp = (UnOpExp + ZeroOrMore((Regex(r'[*/%][&|!%<=>+*/\^-]*[&|!%<>+*/\^-]') | oneOf("* / %")) + UnOpExp)).setParseAction(binopparse_l)
AddExp = (MulExp + ZeroOrMore((Regex(r'[+-][&|!%<=>+*/\^-]*[&|!%<>*/\^]|[+-][&|!%<=>+*/\^-]+[&|!%<>+*/\^-]') | oneOf("+ -")) + MulExp)).setParseAction(binopparse_l)
CmpExp = (AddExp + ZeroOrMore(oneOf('== != < > >= <=') + AddExp)).setParseAction(binopparse_l)
AndExp = (CmpExp + ZeroOrMore((Regex(r'&[&|!%<=>+*/\^-]*[&|!%<>+*/\^-]') | Literal("&")) + CmpExp)).setParseAction(binopparse_l)
Exp << (AndExp + ZeroOrMore((Regex(r'\|[&|!%<=>+*/\^-]*[&|!%<>+*/\^-]') | Literal("|")) + AndExp)).setParseAction(binopparse_l)

def parseFile(fname):
    return Program.parseFile(fname, True)

def parseString(source):
    return Program.parseString(source, True)
