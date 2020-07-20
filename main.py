from PySchTranspiler.tokenizer import lexer

inp = "def print(a):"

lexer.input(inp)


toks = []
for tok in lexer:
    toks.append(tok)

print(toks)

from tokParser import parseToDict

parseConstraint = (
        ("DEF", 1, None),
        ("NAME", 1, "name"),
        ("LPAREN", 1, None),
        ((
            ((("NAME", 1, "arguments"),("COMMA", -1, None)), 0, None),
            ((("INT", 1, "ints"),("COMMA", -1, None)), 0, None)
            ), 0, None),
        ("RPAREN", 1, None),
        ("COLON", 1, None)
    )

print(parseToDict(toks, parseConstraint))