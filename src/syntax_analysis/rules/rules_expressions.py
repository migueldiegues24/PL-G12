def p_expressao(p):
    '''expressao : expressao OR termo_logico
                 | termo_logico'''
    if len(p) == 4:
        p[0] = ('logop', 'or', p[1], p[3])
    else:
        p[0] = p[1]

def p_termo_logico(p):
    '''termo_logico : termo_logico AND fator_logico
                    | fator_logico'''
    if len(p) == 4:
        p[0] = ('logop', 'and', p[1], p[3])
    else:
        p[0] = p[1]

def p_fator_logico(p):
    '''fator_logico : NOT fator_logico
                    | expressao_rel'''
    if len(p) == 3:
        p[0] = ('not', p[2])
    else:
        p[0] = p[1]

def p_expressao_rel(p):
    '''expressao_rel : expressao_arit op_rel expressao_arit
                     | expressao_arit'''
    if len(p) == 4:
        p[0] = ('relop', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_op_rel(p):
    '''op_rel : EQ
              | NE
              | LT
              | LE
              | GT
              | GE'''
    p[0] = p[1]

def p_expressao_arit(p):
    '''expressao_arit : expressao_arit PLUS termo
                      | expressao_arit MINUS termo
                      | termo'''
    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_termo(p):
    '''termo : termo TIMES fator
             | termo DIVIDE fator
             | fator'''
    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_fator_unario(p):
    '''fator : MINUS fator
             | PLUS fator'''
    if p[1] == '-':
        p[0] = ('unop', '-', p[2])
    else:
        p[0] = p[2]

def p_fator(p):
    '''fator : NUMBER
             | BOOL
             | STRING
             | IDENTIFIER
             | IDENTIFIER LPAREN lista_expressoes RPAREN
             | LPAREN expressao RPAREN'''
    if len(p) == 2:
        if isinstance(p[1], bool):
            p[0] = ('bool', p[1])
        elif isinstance(p[1], (int, float)):
            p[0] = ('num', p[1])
        elif isinstance(p[1], str) and p.slice[1].type == 'STRING':
            p[0] = ('string', p[1])
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
