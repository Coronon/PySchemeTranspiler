from typing import TextIO

from .parser import Parser
from .builder import Builder
from .extraCodes import extraC, Arts

class Converter():
    @staticmethod
    def transpile(file: TextIO) -> str:
        Converter.welcome()
        
        toks = Parser.parseFile(file).body
        
        Builder.initState()
        
        compilerCode = ""
        userCode = ""
        
        
        for i in toks:
            userCode += f"{Builder.buildFromNode(i)}\n"
            
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
        Converter.displayArt()
        print("PySchemeTranspiler v1.0 by Rubin Raithel\n\n")
    
    @staticmethod
    def displayArt() -> None:
        print(Arts.dancing)
