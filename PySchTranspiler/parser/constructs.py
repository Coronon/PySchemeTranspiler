from typing import List
from ply.lex import LexToken

class ParseConstruct():

    def __init__(self, cType: str):
        self.type = cType

class SpecialParseConstruct(ParseConstruct):

    def __init__(self, cType: str):
        super().__init__(cType)
        self.content = []
    
    def addContent(self, content: List[ParseConstruct]):
        self.content.append(content)

class FuncConstruct(SpecialParseConstruct):

    def __init__(self, signature: List[LexToken]):
        super().__init__("FUNC")

        self.name = None
        self.arguments = []

        #*Generate signture
        flag = 0
        while len(signature) != 0:
            tok = signature.pop(0)
            if flag == 0:
                if tok.type != "DEF": raise SyntaxError(tok)
                flag = 1
            elif flag == 1:
                if tok.type != "NAME": raise SyntaxError(tok)
                self.name = tok.value
                flag = 2
            elif flag == 2:
                if tok.type != "LPAREN": raise SyntaxError(tok)
                flag = 3
            elif flag == 3:
                if tok.type == "RPAREN":
                    flag = 5
                    continue

                if tok.type != "NAME": raise SyntaxError(tok)
                self.arguments.append(tok.value)
                flag = 4
            elif flag == 4:
                if tok.type == "RPAREN":
                    flag = 5
                    continue

                if tok.type != "COMMA": raise SyntaxError(tok)
                flag = 3
            elif flag == 5:
                if tok.type != "COLON": raise SyntaxError(tok)

    def __repr__(self):
        return f"<FuncConstruct: {self.name}({','.join(self.arguments)})>"