import argparse
from pyschemetranspiler.converter import Converter
from pyschemetranspiler.coloring import Colors, colorT

def main() -> None:
    parser = argparse.ArgumentParser(
        prog='pystranspile',
        description='Transpile simple Python to Scheme(Racket).',
        epilog='Copyright (C) 2020 Rubin Raithel'
        )
    parser.version = 'PySchemeTranspiler v1.1'
    
    parser.add_argument(
        '-version',
        action='version',
        help='display the current version'
        )
    parser.add_argument(
        '-input',
        action='store',
        type=str,
        help='path to file that should be transpiled',
        required=True
        )
    parser.add_argument(
        '-output',
        action='store', 
        type=str,
        help='path to file the transpiled code should be saved in',
        required=True
        )
    
    args = parser.parse_args()
    
    Converter.welcome()
    try:
        with open(args.input, 'r') as file:
            transpiled = Converter.transpile(file)
    except OSError:
        print(colorT("Error accessing the input file", Colors.RED))
        raise SystemExit
    
    try:
        with open(args.output, 'w') as file:
            file.write(transpiled)
    except OSError:
        print(colorT("Error accessing the output file", Colors.RED))
        raise SystemExit
    
    print(colorT("Transpilation successful <3", Colors.BLUE))
