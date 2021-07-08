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
from typing import TextIO, Dict, Set

from .parser import Parser
from .builder import Builder
from .shared import Shared
from .extraCodes import extraC, FlagRequirements, Arts
from .coloring import Colors, colorB, colorT

class Converter():
    @staticmethod
    def transpile(file: TextIO, useMain: bool = True) -> str:
        #* Basic setup
        Shared.currentFile = file.name
        
        #* Pase file to tokens
        toks = Parser.parseFile(file).body
        
        Builder.initState()
        
        compilerCode = "#lang racket\n"
        userCode = ""
        
        #* Transpile tokens to scheme sourcecode one by one
        for i in toks:
            code = Builder.buildFromNode(i)
            if code:
                userCode += code + "\n"
        
        #* Edit code according to build flags    
        buildFlags = Converter.compileBuildFlags(Builder.buildFlags)
        
        if 'NAME_IS_MAIN' in buildFlags:
            compilerCode += f"{extraC.NAME_IS_MAIN}\n"
        if 'GROWABLE_VECTOR_REQUIRE' in buildFlags:
            compilerCode += f"{extraC.GROWABLE_VECTOR_REQUIRE}\n"
        if 'GROWABLE_VECTOR' in buildFlags:
            compilerCode += f"{extraC.GROWABLE_VECTOR}\n"
        if 'DEEPCOPY' in buildFlags:
            compilerCode += f"{extraC.DEEPCOPY}\n"
        if 'PRINT' in buildFlags:
            compilerCode += f"{extraC.PRINT}\n"
        if 'EQUAL' in buildFlags:
            compilerCode += f"{extraC.EQUAL}\n"
        if 'NOT_EQUAL' in buildFlags:
            compilerCode += f"{extraC.NOT_EQUAL}\n"
        if 'IN' in buildFlags:
            compilerCode += f"{extraC.IN}\n"
        if 'INPUT' in buildFlags:
            compilerCode += f"{extraC.INPUT}\n"
        if 'TO_INT' in buildFlags:
            compilerCode += f"{extraC.TO_INT}\n"
        if 'TO_FLOAT' in buildFlags:
            compilerCode += f"{extraC.TO_FLOAT}\n"
        if 'TO_STR' in buildFlags:
            compilerCode += f"{extraC.TO_STR}\n"
        if 'TO_BOOL' in buildFlags:
            compilerCode += f"{extraC.TO_BOOL}\n"
        if 'TO_LIST' in buildFlags:
            compilerCode += f"{extraC.TO_LIST}\n"
        
        if compilerCode == "":
            return userCode.strip()
        
        
        return f"{compilerCode}\n(define (main)\n\n{userCode}\n(void))\n(main)".strip() if useMain else f"{compilerCode}\n{userCode}".strip()
    
    @staticmethod
    def compileBuildFlags(flags: Dict[str, bool]) -> Set[str]:
        ret = set()
        queue = []
        for flag, active in flags.items():
            if active:
                queue.append(flag)
        
        while len(queue) > 0:
            flag = queue.pop()
            ret.add(flag)
            
            for requiredFlag in FlagRequirements.requirements[flag]:
                if requiredFlag not in ret:
                    queue.append(requiredFlag)
        
        return ret
    
    @staticmethod
    def welcome() -> None:
        """Welcome the user with a nice greeting
        """
        Converter.displayArt()
        print(colorT("PySchemeTranspiler v1.3, Copyright (C) 2021 Rubin Raithel", Colors.GREEN))
        print(colorT("This program comes with ABSOLUTELY NO WARRANTY. For details see the 'LICENSE' file.\n\n", Colors.GREEN))
    
    @staticmethod
    def displayArt() -> None:
        """This is art! Stare at the art! You should now feel mentally reinvigorated
        """
        print(Arts.dancing)
