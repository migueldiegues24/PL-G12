def p_programa(p):
    '''programa : newlines_opt lista_unidades'''
    p[0] = ('program', p[2])

def p_lista_unidades(p):
    '''lista_unidades : lista_unidades unidade
                      | unidade'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_unidade(p):
    '''unidade : programa_principal
               | subprograma'''
    p[0] = p[1]

def p_newlines(p):
    '''newlines : newlines NEWLINE
                | NEWLINE'''
    p[0] = None

def p_newlines_opt(p):
    '''newlines_opt : newlines
                    | empty'''
    p[0] = None

def p_empty(p):
    '''empty :'''
    p[0] = None

def p_programa_principal(p):
    '''programa_principal : PROGRAM IDENTIFIER newlines corpo END newlines_opt'''
    p[0] = ('main_program', p[2], p[4])

def p_subprograma_funcao(p):
    '''subprograma : tipo FUNCTION IDENTIFIER LPAREN lista_params RPAREN newlines corpo END newlines_opt
                   | FUNCTION IDENTIFIER LPAREN lista_params RPAREN newlines corpo END newlines_opt'''
    if len(p) == 11:
        p[0] = ('function', p[1], p[3], p[5], p[8])
    else:
        p[0] = ('function', None, p[2], p[4], p[7])

def p_subprograma_subrotina(p):
    '''subprograma : SUBROUTINE IDENTIFIER LPAREN lista_params RPAREN newlines corpo END newlines_opt
                   | SUBROUTINE IDENTIFIER newlines corpo END newlines_opt'''
    if len(p) == 10:
        p[0] = ('subroutine', p[2], p[4], p[7])
    else:
        p[0] = ('subroutine', p[2], [], p[4])

def p_lista_params(p):
    '''lista_params : lista_params COMMA IDENTIFIER
                    | IDENTIFIER
                    | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif p[1] is None:
        p[0] = []
    else:
        p[0] = [p[1]]

def p_corpo(p):
    '''corpo : lista_itens
             | empty'''
    p[0] = ('body', p[1] if p[1] is not None else [])

def p_lista_itens(p):
    '''lista_itens : lista_itens item
                   | item'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_item(p):
    '''item : declaracao
            | statement'''
    p[0] = p[1]
