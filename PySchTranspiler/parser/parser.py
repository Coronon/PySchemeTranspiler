from typing import List, Dict, Any, Iterable, Union, Optional
from ply.lex import LexToken

from .constructs import ParseConstruct, SpecialParseConstruct, FuncConstruct

class Parser():

    def __init__(self, tokens: Iterable[LexToken]):
        self.pTree = []
        self.symboleTable: Dict[str, Any] = {}
        self.tokens = tokens
        self.flag: Optional[str] = None
    
    def parse(self):
        #Split tokens
        stack: List[LexToken] = []
        specialConst: Optional[SpecialParseConstruct] = None
        for tok in self.tokens:
            if specialConst is not None:
                if tok.type == "LCBRACK":
                    continue
                elif tok.type == "RCBRACK":
                    self.pTree.append(specialConst)
                    specialConst = None
                    continue
                elif tok.type == 'SEMICOLON':
                    specialConst.addContent(makeNormalConstruct(stack))
                else:
                    stack.append(tok)
            else:   
                if tok.type == 'COLON':
                    specialConst = self.makeSpecialConstruct(stack)
                elif tok.type == 'SEMICOLON':
                    self.pTree.append(makeNormalConstruct(stack))
                else:
                    stack.append(tok)
    
    def makeNormalConstruct(self, tokens: List[LexToken]) -> ParseConstruct:
        

    def makeSpecialConstruct(self, tokens: List[LexToken]) -> SpecialParseConstruct:
        tConstruct: str = tokens[0].type
        if tConstruct == "DEF":
            return FuncConstruct(tokens)
        elif tConstruct == "FOR":
            print("FOR CONTSTRUCT")
        elif tConstruct == "WHILE":
            print("WHILE CONTSTRUCT")
            
            


tokens = (
   'INT',
   'FLOAT',
   'PLUS',
   'MINUS',
   'TIMES',
   'DIVIDE',
   'EQUALS',
   'SET',
   'NAME',
   'SEMICOLON',
   'COMMA',
   'COLON',
   'LPAREN',
   'RPAREN',
   'LCBRACK',
   'RCBRACK',
   'IF',
   'ELSE',
   'WHILE',
   'FOR',
   'IN',
   'RANGE',
   'DEF'
)
