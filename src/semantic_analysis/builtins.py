from semantic_analysis.symbol_table import Symbol


# Funções intrínsecas Fortran 77 (ANSI X3.9-1978) reconhecidas pelo compilador.
# Cada entrada: (nome, tipo_retorno, tipos_parâmetros).
#
# O standard define famílias com nome específico por tipo (ex: IABS para integer,
# ABS para real) e nomes "genéricos" que aceitam vários tipos. Aqui registamos
# o nome genérico com a assinatura mais comum (real → real para a maioria, e
# integer → integer para as famílias inteiras). Se um exemplo usar a versão
# tipada (IABS, DABS, etc.) basta acrescentá-la à lista.
BUILTINS = [
    # ---- Conversão de tipos ----
    ('INT',    'integer', ['real']),       # parte inteira (truncamento)
    ('IFIX',   'integer', ['real']),       # alias de INT para REAL → INTEGER
    ('REAL',   'real',    ['integer']),    # INTEGER → REAL
    ('FLOAT',  'real',    ['integer']),    # alias de REAL
    ('ICHAR',  'integer', ['integer']),    # carácter → código (limitado sem tipo CHARACTER)

    # ---- Valor absoluto ----
    ('ABS',    'real',    ['real']),
    ('IABS',   'integer', ['integer']),

    # ---- Resto da divisão ----
    ('MOD',    'integer', ['integer', 'integer']),
    ('AMOD',   'real',    ['real',    'real']),

    # ---- Truncamento e arredondamento ----
    ('AINT',   'real',    ['real']),       # trunca para real
    ('ANINT',  'real',    ['real']),       # arredonda para real
    ('NINT',   'integer', ['real']),       # arredonda para inteiro

    # ---- Sinal e diferença positiva ----
    ('SIGN',   'real',    ['real',    'real']),
    ('ISIGN',  'integer', ['integer', 'integer']),
    ('DIM',    'real',    ['real',    'real']),
    ('IDIM',   'integer', ['integer', 'integer']),

    # ---- Máximo e mínimo (versões binárias; o standard permite n>=2 args) ----
    ('MAX',    'real',    ['real',    'real']),
    ('MAX0',   'integer', ['integer', 'integer']),
    ('AMAX1',  'real',    ['real',    'real']),
    ('MIN',    'real',    ['real',    'real']),
    ('MIN0',   'integer', ['integer', 'integer']),
    ('AMIN1',  'real',    ['real',    'real']),

    # ---- Raiz quadrada e exponencial ----
    ('SQRT',   'real',    ['real']),
    ('EXP',    'real',    ['real']),
    ('LOG',    'real',    ['real']),       # logaritmo natural
    ('ALOG',   'real',    ['real']),       # alias de LOG
    ('LOG10',  'real',    ['real']),       # logaritmo decimal
    ('ALOG10', 'real',    ['real']),       # alias de LOG10

    # ---- Trigonometria ----
    ('SIN',    'real',    ['real']),
    ('COS',    'real',    ['real']),
    ('TAN',    'real',    ['real']),
    ('ASIN',   'real',    ['real']),
    ('ACOS',   'real',    ['real']),
    ('ATAN',   'real',    ['real']),
    ('ATAN2',  'real',    ['real',    'real']),

    # ---- Hiperbólicas ----
    ('SINH',   'real',    ['real']),
    ('COSH',   'real',    ['real']),
    ('TANH',   'real',    ['real']),
]


# Regista todas as funções intrínsecas no scope global da tabela.
# Deve ser chamada uma única vez, na construção do analyser.
def register_builtins(table):
    for name, ret_type, params in BUILTINS:
        table.declare(Symbol(name, ret_type, 'function', params=params))
