from PySchemeTranspiler.parser import Parser
from PySchemeTranspiler.builder import Builder

with open('testFile.py', 'r') as file:
    toks = Parser.parseFile(file)

Builder.initState()
for i in toks.body:
    print(Builder.buildFromNode(i))