import ply.yacc as yacc

from syntax_analysis.lexer import tokens

from syntax_analysis.rules.rules_program import *
from syntax_analysis.rules.rules_declarations import *
from syntax_analysis.rules.rules_statements import *
from syntax_analysis.rules.rules_expressions import *

start = 'programa'

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('nonassoc', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
)

def p_error(p):
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    if p:
        print(f"{RED}Erro Sintático:{RESET} Token inesperado {YELLOW}'{p.value}'{RESET} (tipo {p.type}) na linha {p.lineno}")
    else:
        print(f"{RED}Erro Sintático:{RESET} Fim de ficheiro inesperado. Faltou fechar algum bloco (ex: END)?")


parser = yacc.yacc()
