# Regras de compatibilidade de tipos para Fortran 77.
#
# Cada função devolve o tipo resultado da operação, ou None se a operação
# não for válida (cabe ao analyser reportar o erro com a linha apropriada).


NUMERIC = {'integer', 'real'}
LOGICAL = {'logical'}


# + - * /  →  numérico (promoção integer → real se mistos).
def result_type_arith(t1, op, t2):
    if t1 in NUMERIC and t2 in NUMERIC:
        return 'real' if 'real' in (t1, t2) else 'integer'
    return None


# Menos/mais unário sobre expressão numérica → mesmo tipo numérico.
def result_type_unary_arith(t):
    return t if t in NUMERIC else None


# .AND. .OR.  →  exige logical em ambos os operandos, devolve logical.
def result_type_logic(t1, op, t2):
    if t1 in LOGICAL and t2 in LOGICAL:
        return 'logical'
    return None


# .NOT.  →  exige logical, devolve logical.
def result_type_unary_logic(t):
    return 'logical' if t in LOGICAL else None


# .EQ. .NE. .LT. .LE. .GT. .GE.  →  numéricos compatíveis, devolve logical.
def result_type_relop(t1, op, t2):
    if t1 in NUMERIC and t2 in NUMERIC:
        return 'logical'
    return None


# Verifica se LHS = RHS é uma atribuição válida.
# Permite promoção implícita integer <-> real (standard Fortran 77).
def compatible_assign(target_type, value_type):
    if target_type == value_type:
        return True
    if target_type in NUMERIC and value_type in NUMERIC:
        return True
    return False


# Verifica se um tipo pode ser usado como condição (IF, IF-THEN).
# Em Fortran 77 standard tem de ser logical.
def is_condition_type(t):
    return t in LOGICAL


# Verifica se um tipo pode ser usado como índice de array (tem de ser integer).
def is_index_type(t):
    return t == 'integer'
