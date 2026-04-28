from code_generation import ir


# Optimizador da IR.
#
# Estrutura preparada para receber passes — cada pass é uma função que
# recebe uma lista de instruções e devolve outra (possivelmente mais curta).
# Para já não temos passes implementados; o pipeline corre como identidade.


def optimize(code, passes=None):
    if passes is None:
        passes = DEFAULT_PASSES
    for p in passes:
        code = p(code)
    return code


# ----------------------- Passes (placeholders) ---------------------------
# Cada pass mantém a invariante: a sequência produzida é semanticamente
# equivalente à de entrada quando executada na pilha.

# Constant folding: combina dois CONST seguidos de BINOP num único CONST.
def constant_folding(code):
    # Por implementar. Esqueleto:
    # i = 0
    # out = []
    # while i < len(code):
    #     if (i+2 < len(code)
    #         and ir.is_const(code[i]) and ir.is_const(code[i+1])
    #         and ir.opcode(code[i+2]) == 'BINOP'):
    #         ...
    #     else:
    #         out.append(code[i]); i += 1
    # return out
    return code

# Remoção de código morto a seguir a JUMP/HALT/RET até à próxima LABEL.
def dead_code_elimination(code):
    return code

# Identidades algébricas: x*1, x+0, x*0, etc.
def algebraic_simplification(code):
    return code

# Fusão de labels consecutivas e remoção de jumps para a label imediatamente
# seguinte.
def jump_threading(code):
    return code


DEFAULT_PASSES = [
    # Quando os passes estiverem implementados, descomenta:
    # constant_folding,
    # algebraic_simplification,
    # dead_code_elimination,
    # jump_threading,
]
