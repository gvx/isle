from .invoke import arepr, Func, Table, Symbol
from .read_bytecode import make_intermediate_nodes, build_ast
from .rev_visitor import ast_to_source

def write(t, memo, rev_memo):
    if isinstance(t, (Table, Func)):
        if t not in memo:
            index = len(rev_memo) + 1
            memo[t] = index
            rev_memo.append(t)
        return '$' + str(memo[t])
    return arepr(t)

# fun fact: this function is not perfect
# it has a few false positives sometimes
# but no false negatives, so that's good
def is_cyclic(memo, sub, super):
    if sub is super:
        return True
    if sub not in memo:
        return False
    return memo[sub] < memo[super]

def write_table_ex(t, memo, rev_memo, srefs, name):
    yield '$'
    yield str(name)
    if isinstance(t, Func):
        yield ' = replace_closure('
        yield ast_to_source(build_ast(make_intermediate_nodes([('lambda', t.body)]))).strip()
        yield ', ('
        i = -1
        for i, env in enumerate(t.closure):
            if i:
                yield ', '
            yield write(env, memo, rev_memo)
        if i == 0:
            yield ','
        yield '))'
        return
    yield ' = ('
    n = 1
    while n in t:
        if n > 1:
            yield ', '
        if is_cyclic(memo, t[n], t):
            srefs.append((name, n, t[n]))
            yield 'nil'
        else:
            yield write(t[n], memo, rev_memo)
        n += 1
    kw_found = False
    for key, value in t.items():
        if not isinstance(key, int) or not (1 <= key < n):
            if is_cyclic(memo, key, t) or is_cyclic(memo, value, t):
                srefs.append((name, key, value))
                continue
            if n > 1 or kw_found:
                yield ', '
            kw_found = True
            if isinstance(key, Symbol):
                yield arepr(key)[1:]
            else:
                yield '['
                yield write(key, memo, rev_memo)
                yield ']'
            yield '='
            yield write(value, memo, rev_memo)
    if n == 2 and not kw_found:
        yield ','
    yield ')'

def write_key_value_pair(memo, rev_memo, name, key, value):
    yield '$'
    yield str(name)
    if isinstance(key, Symbol):
        yield '.'
        yield arepr(key)[1:]
    else:
        yield '['
        yield write(key, memo, rev_memo)
        yield ']'
    yield ' = '
    yield write(value, memo, rev_memo)


def serialize(t):
    memo = {t: 1}
    rev_memo = [t]
    srefs = []
    result = []

    # phase 1: recursively descend the table structure
    n = 1
    while n <= len(rev_memo):
        result.append(''.join(write_table_ex(rev_memo[n - 1], memo, rev_memo, srefs, n)))
        n += 1

    # phase 2: reverse order
    result = result[::-1]

    # phase 3: add all the tricky cyclic stuff
    for v in srefs:
        result.append(''.join(write_key_value_pair(memo, rev_memo, *v)))

    # phase 4: add something about returning the main table
    if result[-1].startswith('$1 '):
        result[-1] = result[-1][5:]
    else:
        result.append('$1')

    # phase 5: just concatenate everything
    return '\n'.join(result)
