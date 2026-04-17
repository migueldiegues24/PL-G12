def p_statement(p):
    '''statement : stmt_rotulado
                 | stmt_simples'''
    p[0] = p[1]

def p_stmt_rotulado(p):
    '''stmt_rotulado : NUMBER stmt_simples'''
    p[0] = ('labeled', p[1], p[2])

def p_stmt_simples(p):
    '''stmt_simples : atribuicao
                    | stmt_if
                    | stmt_if_block
                    | stmt_do
                    | stmt_goto
                    | stmt_return
                    | stmt_continue
                    | stmt_read
                    | stmt_print
                    | stmt_call'''
    p[0] = p[1]

def p_atribuicao_simples(p):
    '''atribuicao : IDENTIFIER ASSIGN expressao newlines'''
    p[0] = ('assign', ('var', p[1]), p[3])

def p_atribuicao_array(p):
    '''atribuicao : IDENTIFIER LPAREN lista_expressoes RPAREN ASSIGN expressao newlines'''
    p[0] = ('assign', ('index', p[1], p[3]), p[6])

def p_stmt_if_logico(p):
    '''stmt_if : IF LPAREN expressao RPAREN stmt_simples'''
    p[0] = ('if_logico', p[3], p[5])

def p_stmt_if_block_then(p):
    '''stmt_if_block : IF LPAREN expressao RPAREN THEN newlines lista_statements_opt ENDIF newlines'''
    p[0] = ('if_then', p[3], p[7], [])

def p_stmt_if_block_then_else(p):
    '''stmt_if_block : IF LPAREN expressao RPAREN THEN newlines lista_statements_opt ELSE newlines lista_statements_opt ENDIF newlines'''
    p[0] = ('if_then_else', p[3], p[7], p[10])

def p_lista_statements(p):
    '''lista_statements : lista_statements statement
                        | statement'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_lista_statements_opt(p):
    '''lista_statements_opt : lista_statements
                            | empty'''
    p[0] = p[1] if p[1] is not None else []

def p_stmt_do(p):
    '''stmt_do : DO NUMBER IDENTIFIER ASSIGN expressao COMMA expressao newlines
               | DO NUMBER IDENTIFIER ASSIGN expressao COMMA expressao COMMA expressao newlines'''
    if len(p) == 9:
        p[0] = ('do', p[2], p[3], p[5], p[7], None)
    else:
        p[0] = ('do', p[2], p[3], p[5], p[7], p[9])

def p_stmt_goto(p):
    '''stmt_goto : GOTO NUMBER newlines'''
    p[0] = ('goto', p[2])

def p_stmt_return(p):
    '''stmt_return : RETURN newlines'''
    p[0] = ('return',)

def p_stmt_continue(p):
    '''stmt_continue : CONTINUE newlines'''
    p[0] = ('continue',)

def p_stmt_read(p):
    '''stmt_read : READ TIMES COMMA lista_io newlines'''
    p[0] = ('read', p[4])

def p_stmt_print(p):
    '''stmt_print : PRINT TIMES COMMA lista_io newlines'''
    p[0] = ('print', p[4])

def p_lista_io(p):
    '''lista_io : lista_io COMMA item_io
                | item_io'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_item_io(p):
    '''item_io : expressao'''
    p[0] = p[1]

def p_stmt_call(p):
    '''stmt_call : CALL IDENTIFIER newlines
                 | CALL IDENTIFIER LPAREN RPAREN newlines
                 | CALL IDENTIFIER LPAREN lista_expressoes RPAREN newlines'''
    if len(p) == 4:
        p[0] = ('call', p[2], [])
    elif len(p) == 6:
        p[0] = ('call', p[2], [])
    else:
        p[0] = ('call', p[2], p[4])
