# Layout de memória global.
#
# Atribui um offset (na zona global da pilha de operandos da EWVM) a cada
# variável e array do scope corrente. Uma variável simples ocupa 1 slot,
# um array ocupa 'size' slots contíguos.
#
# A EWVM usa a parte de baixo da pilha de operandos como zona global; o
# 'gp' começa em 0 e é incrementado à medida que reservamos espaço.


class GlobalLayout:
    def __init__(self):
        self.offset = {}     # nome → posição inicial
        self.size   = {}     # nome → quantos slots ocupa
        self.type   = {}     # nome → tipo Fortran ('integer'|'real'|'logical')
        self.kind   = {}     # nome → 'var' ou 'array'
        self._next  = 0

    # Reserva slots para um símbolo. 'kind' ∈ {'var','array'}; 'arr_size'
    # só relevante para arrays.
    def allocate(self, name, kind, arr_size=None, type=None):
        if name in self.offset:
            return self.offset[name]
        if kind == 'array':
            n = arr_size
        else:
            n = 1
        self.offset[name] = self._next
        self.size[name]   = n
        self.type[name]   = type
        self.kind[name]   = kind
        self._next       += n
        return self.offset[name]

    # Total de slots a inicializar com PUSHI/PUSHF 0 no arranque.
    def total_slots(self):
        return self._next

    def of(self, name):
        return self.offset[name]

    def __contains__(self, name):
        return name in self.offset


# Layout de uma program unit (FUNCTION ou SUBROUTINE) — relativo a fp.
#
# Convenção de chamada:
#   Para FUNCTIONS o caller empilha:
#     [..., placeholder_retval, arg1, arg2, ..., argN, label]
#   CALL retira a label e atribui fp = sp atual. Logo:
#     argi  → fp[-(N - i + 1)]    (i em 1..N)
#     retval → fp[-(N + 1)]
#   Para SUBROUTINES não há slot de retorno: argi → fp[-(N - i + 1)].
#
# Locais regulares (declarados no corpo) ficam acima de fp em offsets
# 0, 1, 2, ... e são alocados com PUSHN no preâmbulo da função.
class LocalLayout:
    def __init__(self, n_args=0, has_retval=False):
        self.offset = {}     # nome → offset relativo a fp (pode ser negativo)
        self.size   = {}     # nome → quantos slots (1 para escalares)
        self.type   = {}
        self.kind   = {}     # 'param' / 'retval' / 'var' / 'array'
        self.n_args      = n_args
        self.has_retval  = has_retval
        self._next_local = 0

    def allocate_param(self, name, index, type):
        # 'index' é 1-based. arg1 é o parâmetro mais profundo na pilha.
        off = -(self.n_args - index + 1)
        self.offset[name] = off
        self.size[name]   = 1
        self.type[name]   = type
        self.kind[name]   = 'param'
        return off

    def allocate_retval(self, name, type):
        # Slot de retorno: imediatamente abaixo do primeiro argumento.
        off = -(self.n_args + 1)
        self.offset[name] = off
        self.size[name]   = 1
        self.type[name]   = type
        self.kind[name]   = 'retval'
        return off

    def allocate_local(self, name, kind='var', arr_size=None, type=None):
        if name in self.offset:
            return self.offset[name]
        n = arr_size if kind == 'array' else 1
        self.offset[name] = self._next_local
        self.size[name]   = n
        self.type[name]   = type
        self.kind[name]   = kind
        self._next_local += n
        return self.offset[name]

    def total_locals(self):
        return self._next_local

    def of(self, name):
        return self.offset[name]

    def __contains__(self, name):
        return name in self.offset
