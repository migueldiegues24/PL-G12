import ply.lex as lex

reserved = {
    'program': 'PROGRAM',
    'read': 'READ',
    'print': 'PRINT',
    'integer': 'INTEGER',
    'real': 'REAL',
    'logical': 'LOGICAL',
    'if': 'IF',
    'then': 'THEN',
    'else': 'ELSE',
    'endif': 'ENDIF',
    'do': 'DO',
    'goto': 'GOTO',
    'continue': 'CONTINUE',
    'end': 'END',
    'function': 'FUNCTION',
    'subroutine': 'SUBROUTINE',
    'return': 'RETURN'
}

tokens = [
    'IDENTIFIER', 'NUMBER', 'STRING', 'BOOL',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'ASSIGN',
    'EQ', 'LE', 'GT', 'AND',
    'LPAREN', 'RPAREN', 'COMMA',
    'NEWLINE'
] + list(reserved.values())

t_ignore = ' \t'

t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_ASSIGN  = r'='
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_COMMA   = r','

t_EQ  = r'\.EQ\.'
t_LE  = r'\.LE\.'
t_GT  = r'\.GT\.'
t_AND = r'\.AND\.'

def t_BOOL(t):
    r'\.(TRUE|FALSE)\.'
    t.value = True if t.value == '.TRUE.' else False
    return t

def t_STRING(t):
    r"'[^']*'"
    t.value = t.value[1:-1]
    return t

def t_NUMBER(t):
    r'\d+(\.\d+)?'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    palavra_em_minusculas = t.value.lower()
    t.type = reserved.get(palavra_em_minusculas, 'IDENTIFIER')
    return t



def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

def t_error(t):
    coluna = find_column(t.lexer.lexdata, t)
    
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    

    print(f"{RED}Erro léxico:{RESET} Caractere não permitido {YELLOW}'{t.value[0]}'{RESET} na linha {t.lexer.lineno}, coluna {coluna}")
    
    t.lexer.skip(1)
    
def find_column(input_string, token):
    line_start = input_string.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1

lexer = lex.lex()