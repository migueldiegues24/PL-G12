from code_generation import ir


# Tradução IR → assembly EWVM.
#
# Recebe a lista de instruções IR + o layout global e devolve uma lista
# de strings, uma por linha do programa EWVM.


# Mapas IR-op → instrução EWVM, separando inteiro/real onde aplicável.
_BINOP_INT = {'+': 'ADD',  '-': 'SUB',  '*': 'MUL',  '/': 'DIV'}
_BINOP_FLT = {'+': 'FADD', '-': 'FSUB', '*': 'FMUL', '/': 'FDIV'}

_RELOP_INT = {
    '.EQ.': 'EQUAL',
    '.NE.': 'EQUAL\nNOT',     # !=  →  ==  +  NOT
    '.LT.': 'INF',
    '.LE.': 'INFEQ',
    '.GT.': 'SUP',
    '.GE.': 'SUPEQ',
}
_RELOP_FLT = {
    '.EQ.': 'FEQ',
    '.NE.': 'FEQ\nNOT',
    '.LT.': 'FINF',
    '.LE.': 'FINFEQ',
    '.GT.': 'FSUP',
    '.GE.': 'FSUPEQ',
}


# Funções intrínsecas: nome Fortran → instrução(ões) EWVM.
# Para o que for além disto (SIN, COS, ...), expandimos quando precisarmos.
_BUILTIN = {
    ('MOD',  'integer'): 'MOD',
    ('ABS',  'real'):    'FABS',
    ('IABS', 'integer'): 'ABS',
    ('SQRT', 'real'):    'FSQRT',
    ('REAL', 'real'):    'ITOF',
    ('FLOAT','real'):    'ITOF',
    ('INT',  'integer'): 'FTOI',
    ('IFIX', 'integer'): 'FTOI',
}


class Emitter:
    def __init__(self, layout):
        self.layout = layout
        self.out    = []

    def emit(self, code):
        self.out.append('start')
        for instr in code:
            self._dispatch(instr)
        # 'stop' é gerado pelo HALT; se faltar, garantimos.
        if not self.out or self.out[-1] != 'stop':
            self.out.append('stop')
        return self.out

    def _w(self, line):
        self.out.append(line)

    def _dispatch(self, instr):
        op = instr[0]
        method = getattr(self, f'_op_{op}', None)
        if method is None:
            raise NotImplementedError(f"IR op não suportada pelo emitter: {op}")
        method(instr)

    # ---------- Empilhar / armazenar ----------
    def _op_CONST(self, instr):
        _, value, kind = instr
        if kind == 'integer' or kind == 'logical':
            self._w(f"PUSHI {int(value)}")
        elif kind == 'real':
            self._w(f"PUSHF {float(value)}")
        elif kind == 'string':
            # PUSHS espera string entre aspas.
            escaped = value.replace('"', '\\"')
            self._w(f'PUSHS "{escaped}"')
        else:
            raise NotImplementedError(f"CONST de tipo {kind}")

    def _op_LOAD(self, instr):
        _, name, _t = instr
        self._w(f"PUSHG {self.layout.of(name)}")

    def _op_STORE(self, instr):
        _, name, _t = instr
        self._w(f"STOREG {self.layout.of(name)}")

    def _op_LOADADDR(self, instr):
        _, name = instr
        # PUSHGP + PUSHI offset + PADD = Endereço base da variável
        self._w("PUSHGP")
        self._w(f"PUSHI {self.layout.of(name)}")
        self._w("PADD")

    def _op_LOADIDX(self, instr):
        _, name, _t = instr
        # 1. Ajustar o índice (Fortran é 1-based, EWVM a memória começa em 0)
        # Stack: [..., Indice]
        self._w("PUSHI 1")
        self._w("SUB")
        # Stack: [..., Indice_ajustado]
        
        # 2. Obter o Endereço Base do Array
        self._w("PUSHGP")
        self._w(f"PUSHI {self.layout.of(name)}")
        self._w("PADD") 
        # Stack: [..., Indice_ajustado, Endereco_Base]
        
        # 3. Inverter para colocar o Endereço por baixo do Índice
        self._w("SWAP")
        # Stack: [..., Endereco_Base, Indice_ajustado]
        
        # 4. Somar o índice ao Endereço Base para obter a posição final
        self._w("PADD")
        
        # 5. Ler o valor que está nessa posição de memória
        self._w("LOAD 0")


    def _op_STOREIDX(self, instr):
        _, name, _t = instr
        # Neste momento, a stack tem: [..., Valor_a_guardar, Indice]
        
        # 1. Ajustar o índice (1-based para 0-based)
        self._w("PUSHI 1")
        self._w("SUB")
        # Stack: [..., Valor, Indice_ajustado]
        
        # 2. Obter o Endereço Base do Array
        self._w("PUSHGP")
        self._w(f"PUSHI {self.layout.of(name)}")
        self._w("PADD")
        # Stack: [..., Valor, Indice_ajustado, Endereco_Base]
        
        # 3. Inverter para colocar o Endereço por baixo do Índice (crucial para o PADD)
        self._w("SWAP")
        # Stack: [..., Valor, Endereco_Base, Indice_ajustado]
        
        # 4. Somar para ter o endereço de destino final
        self._w("PADD") 
        # Stack: [..., Valor, Endereco_Destino]
        
        # 5. Inverter a stack para [..., Endereco_Destino, Valor]
        self._w("SWAP")
        
        # 6. Guardar o valor
        self._w("STORE 0")

    # ---------- Aritmética / lógica ----------
    def _op_BINOP(self, instr):
        _, op, t = instr
        if t == 'real':
            self._w(_BINOP_FLT[op])
        else:
            self._w(_BINOP_INT[op])

    def _op_NEG(self, instr):
        _, t = instr
        if t == 'real':
            self._w("PUSHF 0.0"); self._w("SWAP"); self._w("FSUB")
        else:
            self._w("PUSHI 0"); self._w("SWAP"); self._w("SUB")

    def _op_I2F(self, instr):
        self._w("ITOF")

    def _op_RELOP(self, instr):
        _, op, t = instr
        seq = (_RELOP_FLT if t == 'real' else _RELOP_INT)[op]
        for line in seq.split('\n'):
            self._w(line)

    def _op_LOGOP(self, instr):
        _, op = instr
        # AND/OR já operam sobre 0/1.
        self._w('AND' if op == 'and' else 'OR')

    def _op_NOT(self, _instr):
        self._w("NOT")

    # ---------- Control flow ----------
    def _op_LABEL(self, instr):
        _, name = instr
        self._w(f"{name}:")

    def _op_JUMP(self, instr):
        _, name = instr
        self._w(f"JUMP {name}")

    def _op_JZ(self, instr):
        _, name = instr
        self._w(f"JZ {name}")

    # ---------- IO ----------
    def _op_READ(self, instr):
        _, t, _name = instr
        self._w("READ")
        if t == 'integer':
            self._w("ATOI")
        elif t == 'real':
            self._w("ATOF")
        # string: o READ já deixa o endereço no topo

    def _op_WRITE(self, instr):
        _, t = instr
        if t == 'integer' or t == 'logical':
            self._w("WRITEI")
        elif t == 'real':
            self._w("WRITEF")
        elif t == 'string':
            self._w("WRITES")

    def _op_WRITELN(self, _instr):
        self._w("WRITELN")

    # ---------- Funções ----------
    def _op_CALL_BUILTIN(self, instr):
        _, name, n_args, ret_t = instr
        key = (name, ret_t)
        if key in _BUILTIN:
            self._w(_BUILTIN[key])
        else:
            raise NotImplementedError(f"Built-in não mapeada: {name} → {ret_t}")

    def _op_CALL(self, instr):
        # Por implementar quando atacarmos funções do utilizador.
        raise NotImplementedError("CALL ainda não implementado nesta fase")

    def _op_RET(self, _instr):
        raise NotImplementedError("RET ainda não implementado nesta fase")

    def _op_HALT(self, _instr):
        if self.out and self.out[-1] != 'stop':
            self._w("stop")