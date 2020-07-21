from PySchemeTranspiler.parser import Parser
from PySchemeTranspiler.builder import Builder

with open('testFile.py', 'r') as file:
    toks = Parser.parseFile(file)

print(Builder.buildFromNode(toks.body[0]))