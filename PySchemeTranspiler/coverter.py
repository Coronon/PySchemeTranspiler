from typing import TextIO

from .parser import Parser
from .builder import Builder
from .shared import Shared
from .extraCodes import extraC, Arts
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
        buildFlags = Builder.buildFlags
        
        if buildFlags['PRINT']:
            compilerCode += f"{extraC.PRINT}\n"
        if buildFlags['NOT_EQUAL']:
            compilerCode += f"{extraC.NOT_EQUAL}\n"
        
        if compilerCode == "":
            return userCode
        
        
        return f"{compilerCode}\n{userCode}".strip()
    
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
