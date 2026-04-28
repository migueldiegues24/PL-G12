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
