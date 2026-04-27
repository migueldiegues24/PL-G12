from semantic_analysis.semantic_errors import SemanticError


# Representa uma entrada na tabela de símbolos: variável, array, parâmetro
# ou nome de função/subrotina. O campo 'kind' distingue os casos.
class Symbol:
    def __init__(self, name, type, kind, initialized=False, size=None, params=None, line=None):
        self.name        = name
        self.type        = type             # integer/real/logical (None para subroutine)
        self.kind        = kind             # var/array/function/subroutine/param
        self.initialized = initialized      # só relevante para variáveis
        self.size        = size             # só relevante para arrays
        self.params      = params           # só relevante para funções/subrotinas
        self.line        = line

    def __repr__(self):
        extra = ""
        if self.kind == 'array':
            extra = f"({self.size})"
        elif self.kind in ('function', 'subroutine'):
            extra = f"({', '.join(self.params or [])})"
        return f"Symbol({self.kind} {self.type} {self.name}{extra})"


# Tabela de símbolos para Fortran 77.
#
# Em Fortran 77 standard cada program unit (PROGRAM, FUNCTION, SUBROUTINE) tem
# um scope isolado: não acede a variáveis do chamador nem do programa principal,
# só à sua própria área e aos NOMES das funções/subrotinas (que vivem no scope
# global). Como funções não aninham, a pilha tem no máximo dois scopes em uso:
#
#   índice 0  →  global  (apenas funções/subrotinas)
#   índice -1 →  program unit corrente (variáveis, arrays, parâmetros, labels)
#
# O lookup respeita esta regra olhando só para esses dois scopes.
class SymbolTable:
    def __init__(self):
        self.__table    = [{}]          # pilha de scopes para símbolos
        self.__labels   = [{}]          # pilha de scopes para labels (1-1 com __table)
        self.__names    = ["global"]    # nomes dos scopes 

    # Entra num novo scope (program unit). Chamar em PROGRAM/FUNCTION/SUBROUTINE.
    def push_scope(self, name="local"):
        self.__table.append({})
        self.__labels.append({})
        self.__names.append(name)

    # Sai do scope atual. O scope global não pode ser removido.
    def pop_scope(self):
        if len(self.__table) == 1:
            raise SemanticError("Tentativa de remover o scope global")
        self.__table.pop()
        self.__labels.pop()
        self.__names.pop()

    @property
    def current_scope_name(self):
        return self.__names[-1]

    @property
    def depth(self):
        return len(self.__table)

    # Declara um símbolo no scope corrente. Falha se o nome já existir
    # nesse scope (shadowing do global é permitido, igualar localmente não).
    def declare(self, symbol):
        top = self.__table[-1]
        if symbol.name in top:
            raise SemanticError(
                f"Variável '{symbol.name}' já declarada no scope '{self.current_scope_name}'",
                symbol.line
            )
        top[symbol.name] = symbol

    # Procura um símbolo seguindo a regra de visibilidade do Fortran 77:
    # primeiro o scope corrente, depois o global. Scopes intermédios (se
    # alguma vez existirem) são ignorados de propósito — uma função não
    # vê variáveis locais do programa principal.
    def lookup(self, id, line=None):
        if id in self.__table[-1]:
            return self.__table[-1][id]
        if id in self.__table[0]:
            return self.__table[0][id]
        raise SemanticError(f"Variável '{id}' não declarada", line)

    # Procura apenas no scope corrente, sem fallback para o global.
    # Útil para detetar redeclarações ou verificar se um parâmetro já foi declarado.
    def lookup_local(self, id):
        return self.__table[-1].get(id)

    # Regista uma label de statement (ex: "10 CONTINUE") no scope corrente.
    # Labels têm namespace próprio — não colidem com nomes de variáveis.
    def declare_label(self, label, stmt_kind, line=None):
        top = self.__labels[-1]
        if label in top:
            raise SemanticError(
                f"Label {label} duplicada no scope '{self.current_scope_name}'",
                line
            )
        top[label] = (stmt_kind, line)

    # Marca uma variável como inicializada (atribuída pelo menos uma vez).
    # Útil para avisar uso antes de inicializar. Procura segue a mesma
    # regra do lookup: corrente + global.
    def initialize(self, name, line=None):
        for table in (self.__table[-1], self.__table[0]):
            if name in table:
                if table[name].kind != "var":
                    raise SemanticError(f"O identificador não é uma variável: {name}", line)
                table[name].initialized = True
                return
        raise SemanticError(f"Variável não declarada: {name}", line)

    # Procura uma label apenas no scope corrente. Em Fortran 77 labels são
    # estritamente locais à program unit — não atravessam funções.
    def lookup_label(self, label):
        return self.__labels[-1].get(label)

    # Devolve uma cópia dos símbolos do scope corrente (para debug/logging).
    def local_symbols(self):
        return dict(self.__table[-1])

    # Devolve uma cópia das labels do scope corrente.
    def local_labels(self):
        return dict(self.__labels[-1])

    def __repr__(self):
        return f"SymbolTable(depth={self.depth}, top='{self.current_scope_name}', symbols={list(self.__table[-1].keys())})"
