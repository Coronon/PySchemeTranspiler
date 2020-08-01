from ast import AST

from .shared import Shared
from .coloring import Colors, colorB, colorT

class ConversionException(Exception):
    pass

def throw(expt: Exception, node: AST):
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
