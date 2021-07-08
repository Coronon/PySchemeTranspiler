# PySchemeTranspiler, Transpile simple Python to Scheme(Racket)
# Copyright (C) 2021  Rubin Raithel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import argparse
from pyschemetranspiler.converter import Converter
from pyschemetranspiler.coloring import Colors, colorT

def main() -> None:
    parser = argparse.ArgumentParser(
        prog='pystranspile',
        description='Transpile simple Python to Scheme(Racket).',
        epilog='Copyright (C) 2021 Rubin Raithel'
        )
    parser.version = 'PySchemeTranspiler v1.3'
    
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
    parser.add_argument(
        '-exportable',
        action='store_true',
        help='don\'t wrap all usercode in a main function to allow easier exports (this might cause extra outputs)'
    )
    
    args = parser.parse_args()
    
    Converter.welcome()
    try:
        with open(args.input, 'r') as file:
            transpiled = Converter.transpile(file, not args.exportable)
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
