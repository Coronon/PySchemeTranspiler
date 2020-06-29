import ply.lex as lex

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

t_PLUS      = r'\+'
t_MINUS     = r'\-'
t_TIMES     = r'\*'
t_DIVIDE    = r'\/'
t_EQUALS    = r'\=\='
t_SET       = r'\='
t_SEMICOLON = r'\;'
t_COMMA     = r'\,'
t_COLON     = r'\:'
t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_LCBRACK   = r'\{'
t_RCBRACK   = r'\}'

reserved = {
   'if'    : 'IF',
   'else'  : 'ELSE',
   'while' : 'WHILE',
   'for'   : 'FOR',
   'in'    : 'IN',
   'range' : 'RANGE',
   'def'   : 'DEF'
}

def t_NAME(t):
    r'(^|(?<=[+\(\s\,]))[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'NAME')
    return t

def t_FLOAT(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'

# Error handling rule
def t_error(t):
    raise ValueError(f"Illegal character '{t.value[0]}'")

lexer = lex.lex()

inp = input("TOKENIZE: ")

lexer.input(inp)


toks = []
for tok in lexer:
    toks.append(tok)

from parser.constructs import FuncConstruct

t = FuncConstruct(toks)