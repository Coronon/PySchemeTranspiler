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
from ast import AST

from .shared import Shared
from .coloring import Colors, colorB, colorT

class ConversionException(Exception):
    pass

def throw(expt: Exception, node: AST) -> None:
    print(colorT(f"[{expt.__class__.__name__}] {expt}", Colors.RED))
    
    #? Highlight offending line
    try:
        with open(Shared.currentFile, "r") as file:
            for i, line in enumerate(file):
                if i == node.lineno-1:
                    infoStr = f"{node.lineno}>{node.col_offset}: "
                    leadingSpaces = len(line) - len(line.lstrip(' '))
                    print(colorT(infoStr, Colors.ORANGE), line.strip())
                    print(' ' * (len(infoStr) + node.col_offset - leadingSpaces + 1) + colorT('^', Colors.GREEN))
    except:
        print(colorT(f"Could not print offending code at: {node.lineno}>{node.col_offset}", Colors.ORANGE))
    raise SystemExit()

def warn(warnType: str, warn: Exception, node: AST) -> None:
    print(colorT(f"[{warnType}] {warn}", Colors.ORANGE))
    
    #? Highlight offending line
    try:
        with open(Shared.currentFile, "r") as file:
            for i, line in enumerate(file):
                if i == node.lineno-1:
                    infoStr = f"{node.lineno}>{node.col_offset}: "
                    leadingSpaces = len(line) - len(line.lstrip(' '))
                    print(colorT(infoStr, Colors.ORANGE), line.strip())
                    print(' ' * (len(infoStr) + node.col_offset - leadingSpaces + 1) + colorT('^', Colors.GREEN))
    except:
        print(colorT(f"Could not print maybe offending code at: {node.lineno}>{node.col_offset}", Colors.ORANGE))
