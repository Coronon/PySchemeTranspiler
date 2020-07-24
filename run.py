from PySchemeTranspiler import transpile

with open('testFile.py', 'r') as file:
    print(transpile(file))