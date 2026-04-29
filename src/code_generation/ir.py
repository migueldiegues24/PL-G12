# Representação Intermédia (IR) do compilador.
#
# Lista linear de instruções de "alto nível", ainda com nomes simbólicos
# (variáveis e labels) por resolver. O builder traduz a AST anotada para
# esta forma; o optimizer pode reescrevê-la em passes; o emitter converte
# cada instrução para uma ou mais instruções da EWVM.
#
# Cada instrução é um tuplo cujo primeiro elemento é o opcode (string).
# Mantemos o tipo Fortran ('integer'|'real'|'logical'|'string') quando é
# preciso para escolher a instrução EWVM certa (ADD vs FADD, etc).
#
# Convenção de avaliação: tal como na EWVM, as instruções operam sobre
# uma pilha imaginária — a IR é estritamente postfix.


# ----------------------- Construtores de instruções ----------------------

# Empilha um literal. 'kind' ∈ {'integer','real','logical','string'}.
def CONST(value, kind):
    return ('CONST', value, kind)

# Empilha o valor de uma variável global pelo nome simbólico.
def LOAD(name, type):
    return ('LOAD', name, type)

# Pop e armazena no global 'name'.
def STORE(name, type):
    return ('STORE', name, type)

# Equivalentes para variáveis locais: o offset é relativo a fp e já vem
# resolvido pelo builder (negativo para parâmetros e slot de retorno,
# não-negativo para locais regulares).
def LOADL(name, type, offset):
    return ('LOADL', name, type, offset)

def STOREL(name, type, offset):
    return ('STOREL', name, type, offset)

# Empilha o endereço base do array (PUSHGA na EWVM).
def LOADADDR(name):
    return ('LOADADDR', name)

# Pop índice; carrega elemento. 'type' = tipo do elemento.
def LOADIDX(name, type):
    return ('LOADIDX', name, type)

# Pop valor + índice; guarda elemento.
def STOREIDX(name, type):
    return ('STOREIDX', name, type)

# Operação aritmética binária. op ∈ {'+','-','*','/'}.
# 'type' é o tipo resultado ('integer' ou 'real').
def BINOP(op, type):
    return ('BINOP', op, type)

# Comparação relacional. op ∈ {'.EQ.','.NE.','.LT.','.LE.','.GT.','.GE.'}.
# 'operand_type' é o tipo dos operandos (integer ou real).
def RELOP(op, operand_type):
    return ('RELOP', op, operand_type)

# Operação lógica binária. op ∈ {'and','or'}.
def LOGOP(op):
    return ('LOGOP', op)

# Negação lógica.
def NOT():
    return ('NOT',)

# Negação aritmética unária. type ∈ {'integer','real'}.
def NEG(type):
    return ('NEG', type)

# Promoção integer → real.
def I2F():
    return ('I2F',)

# Define uma label (alvo de jumps).
def LABEL(name):
    return ('LABEL', name)

# Salto incondicional.
def JUMP(label):
    return ('JUMP', label)

# Pop valor; salta para 'label' se 0/falso.
def JZ(label):
    return ('JZ', label)

# IO. 'type' é o tipo do valor a ler/imprimir; 'string' imprime literais.
def READ(type, name):
    return ('READ', type, name)

def WRITE(type):
    return ('WRITE', type)

# Imprime newline (usado depois de cada PRINT do Fortran 77).
def WRITELN():
    return ('WRITELN',)

# Empilha o endereço de código de uma label (PUSHA na EWVM).
def PUSHA(label):
    return ('PUSHA', label)

# Chamada de subprograma do utilizador.
# A label tem de ter sido empilhada antes (com PUSHA). A EWVM faz o resto:
# guarda pc/fp na call stack, atualiza pc para o endereço, e fp para sp.
# 'n_args' e 'has_retval' são informação para o emitter cuidar da limpeza.
def CALL_USER(name, n_args, has_retval):
    return ('CALL_USER', name, n_args, has_retval)

# Retorno de subprograma: restaura fp e pc, sp = fp.
def RETURN():
    return ('RETURN',)

# Aloca n slots inicializados a 0 na pilha de operandos (frame de locais).
def PUSHN(n):
    return ('PUSHN', n)

# Descarta n valores do topo da pilha de operandos.
def POPN(n):
    return ('POPN', n)

# Marca fim do programa (HALT na EWVM, ou STOP).
def HALT():
    return ('HALT',)

# Pseudo-instruções para o início/fim do programa principal e para uma
# eventual chamada a função built-in (MOD, SQRT, ...) — o emitter decide
# como expandir.
def CALL_BUILTIN(name, n_args, return_type):
    return ('CALL_BUILTIN', name, n_args, return_type)


# ------------------- Helpers para o optimizer -----------------------------
# Permite a futuros passes inspecionar o opcode e os campos sem assumir
# posições fixas em todo o lado.

def opcode(instr):
    return instr[0]

def is_const(instr):
    return instr[0] == 'CONST'

def const_value(instr):
    return instr[1]

def const_type(instr):
    return instr[2]
