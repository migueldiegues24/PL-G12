def p_expressao_logica(p):
    '''expressao_logica : expressao_logica OR termo_logico
                        | termo_logico'''
    if len(p) == 4:
        p[0] = ('logop', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_termo_logico(p):
    '''termo_logico : termo_logico AND fator_logico
                    | fator_logico'''
    if len(p) == 4:
        p[0] = ('logop', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_fator_logico(p):
    '''fator_logico : NOT unidade_logica
                    | unidade_logica'''
    if len(p) == 3:
        p[0] = ('not', p[1], p[2])
    else:
        p[0] = p[1]

def p_unidade_logica(p):
    '''unidade_logica : comparacao
                      | BOOL
                      | IDENTIFIER
                      | LPAREN expressao_logica RPAREN'''
    if len(p) == 2:
        if isinstance(p[1], bool):
            p[0] = ('bool', p[1])
        elif isinstance(p[1], str):
            p[0] = ('var', p[1])
        else:
            p[0] = p[1] 
    else:
        p[0] = p[2]

def p_comparacao(p):
    '''comparacao : expressao EQ expressao
                  | expressao LE expressao
                  | expressao GT expressao'''
    p[0] = ('relop', p[2], p[1], p[3])

# =========================================================

def p_expressao_aritmetica(p):
    '''expressao : expressao PLUS termo
                 | expressao MINUS termo
                 | termo'''
    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_termo_aritmetico(p):
    '''termo : termo TIMES fator
             | termo DIVIDE fator
             | fator'''
    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_fator(p):
    '''fator : NUMBER
             | IDENTIFIER
             | IDENTIFIER LPAREN lista_expressoes RPAREN
             | LPAREN expressao RPAREN'''
    if len(p) == 2:
        if isinstance(p[1], (int, float)):
            p[0] = ('num', p[1])
        else:
            p[0] = ('var', p[1])
    elif len(p) == 5:
        p[0] = ('call_or_array', p[1], p[3])
    else:
        p[0] = p[2]

def p_lista_expressoes(p):
    '''lista_expressoes : lista_expressoes COMMA expressao
                        | expressao'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]