def p_declaracao(p):
    '''declaracao : tipo lista_vars newlines'''
    p[0] = ('decl', p[1], p[2])

def p_tipo(p):
    '''tipo : INTEGER
            | REAL
            | LOGICAL'''
    p[0] = p[1].lower()

def p_lista_vars(p):
    '''lista_vars : lista_vars COMMA var_decl
                  | var_decl'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_var_decl(p):
    '''var_decl : IDENTIFIER
                | IDENTIFIER LPAREN NUMBER RPAREN'''
    if len(p) == 2:
        p[0] = ('var_decl', p[1])
    else:
        p[0] = ('array_decl', p[1], p[3])
