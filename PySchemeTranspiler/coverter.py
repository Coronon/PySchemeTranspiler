from typing import TextIO, Dict, Set

from .parser import Parser
from .builder import Builder
from .shared import Shared
from .extraCodes import extraC, FlagRequirements, Arts
from .coloring import Colors, colorB, colorT

class Converter():
    @staticmethod
    def transpile(file: TextIO) -> str:
        #* Basic setup
        Shared.currentFile = file.name
        Converter.welcome()
        
        #* Pase file to tokens
        toks = Parser.parseFile(file).body
        
        Builder.initState()
        
        compilerCode = ""
        userCode = ""
        
        #* Transpile tokens to scheme sourcecode one by one
        for i in toks:
            userCode += f"{Builder.buildFromNode(i)}\n"
        
        #* Edit code according to build flags    
        buildFlags = Converter.compileBuildFlags(Builder.buildFlags)
        
        if 'PRINT' in buildFlags:
            compilerCode += f"{extraC.PRINT}\n"
        if 'NOT_EQUAL' in buildFlags:
            compilerCode += f"{extraC.NOT_EQUAL}\n"
        if 'INPUT' in buildFlags:
            compilerCode += f"{extraC.INPUT}\n"
        
        if compilerCode == "":
            return userCode.strip()
        
        
        return f"{compilerCode}\n{userCode}".strip()
    
    @staticmethod
    def compileBuildFlags(flags: Dict[str, bool]) -> Set[str]:
        ret = set()
        for flag, active in flags.items():
            if active:
                ret = ret | {flag} | FlagRequirements.requirements[flag]
        
        return ret
    
    @staticmethod
    def welcome() -> None:
        """Welcome the user with a nice greeting
        """
        Converter.displayArt()
        print(colorT("PySchemeTranspiler v1.0 by Rubin Raithel\n\n", Colors.GREEN))
    
    @staticmethod
    def displayArt() -> None:
        """This is art! Stare at the art! You should now feel mentally reinvigorated
        """
        print(Arts.dancing)
