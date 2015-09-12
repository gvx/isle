from .parse import parseFile, parseString
from .visitor import fixtags, flattenbody
from .read_bytecode import make_intermediate_nodes, build_ast
from .rev_visitor import ast_to_source

__all__ = ['format_isle']

def format_isle(mod):
    return ast_to_source(mod).strip()

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='auto-format Isle modules')
    parser.add_argument('infile', nargs='?', default='-', metavar='INFILE',
                   help='the input file, omit or use - for stdin')
    parser.add_argument('--out', '-o', default='-', metavar='OUTFILE',
                   help='the output file, omit or use - for stdout')
    parser.add_argument('--in-place', '-i', action='store_true',
                   help='change INFILE in place and ignore any given OUTFILE')

    args = parser.parse_args()

    if args.in_place:
        args.out = args.infile

    if args.infile == '-':
        source = parseString(sys.stdin.read())
    else:
        source = parseFile(args.infile)

    new_source = format_isle(source)

    if args.out == '-':
        sys.stdout.write(new_source)
    else:
        with open(args.out, 'w') as f:
            f.write(new_source)
