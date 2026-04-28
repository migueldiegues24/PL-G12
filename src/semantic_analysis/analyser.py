from semantic_analysis.symbol_table import Symbol, SymbolTable
from semantic_analysis.semantic_errors import SemanticErrorReporter, SemanticError
from semantic_analysis.builtins import register_builtins
from semantic_analysis.type_rules import (
    result_type_arith,
    result_type_logic,
    result_type_relop,
    compatible_assign,
    is_condition_type,
    is_index_type,
)
# Análise semântica do programa Fortran 77.
#
# Percorre a AST produzida pelo parser, valida regras semânticas (declarações,
# tipos, labels, scopes) e devolve uma AST anotada + tabela de símbolos para
# a fase de tradução de código.


class SemanticAnalyser:
    def __init__(self):
        self.table = SymbolTable()
        self.reporter = SemanticErrorReporter()
        self.current_function = None      # nome da função em análise (para validar 'CONVRT = VAL')
        register_builtins(self.table)     # MOD e companhia no global

    # Entry point. Devolve (ast_anotada, tabela, reporter).
    def analyse(self, ast):
        self._pass1_collect_globals(ast)
        annotated = self._pass2_visit(ast)
        return annotated, self.table, self.reporter


    # =====================================================================
    # PASSAGEM 1
    # Recolha de funções/subrotinas no scope global. Necessária antes da
    # passagem 2 para resolver chamadas a funções definidas DEPOIS do main.
    # =====================================================================
    def _pass1_collect_globals(self, ast):
        for unit in ast[1]:
            tag = unit[0]
            if tag == 'function':
                self._declare_function(unit)
            elif tag == 'subroutine':
                self._declare_subroutine(unit)

    def _declare_function(self, node):
        tag, return_type, name, args, body = node 
        
        func_symbol = Symbol(
            name=name,
            type=return_type,
            king='function',
            params=args
        )
        self.table.declare(func_symbol)

    def _declare_subroutine(self, node):
        # Supondo que a AST para subroutine é: ('subroutine', NOME, args, body)
        tag, name, args, body = node
        
        sub_symbol = Symbol(
            name=name,
            type=None,         # Subrotinas não têm tipo de retorno
            kind='subroutine',
            params=args
        )
        
        self.table.declare(sub_symbol)


    # =====================================================================
    # PASSAGEM 2
    # Visitor da AST. Cada visit_X devolve a versão anotada do nó (ou o
    # nó tal-qual se não houver anotação a fazer).
    # =====================================================================
    def _pass2_visit(self, node):
        return self.visit(node)

    def visit(self, node):
        if not isinstance(node, tuple):
            return node
        method = getattr(self, f'visit_{node[0]}', self.generic_visit)
        try:
            return method(node)
        except SemanticError as e:
            self.reporter.errors.append(e)
            print(e.formatted())
            return node

    def generic_visit(self, node):
        return node


    # ---------- Program units ----------
    def visit_program(self, node):
        pass

    def visit_main_program(self, node):
        pass

    def visit_function(self, node):
        pass

    def visit_subroutine(self, node):
        pass

    def visit_body(self, node):
        pass


    # ---------- Declarações ----------
    def visit_decl(self, node):
        pass


    # ---------- Statements ----------
    def visit_labeled(self, node):
        pass

    def visit_assign(self, node):
        pass

    def visit_if_logico(self, node):
        pass

    def visit_if_then(self, node):
        pass

    def visit_if_then_else(self, node):
        pass

    def visit_do(self, node):
        pass

    def visit_goto(self, node):
        pass

    def visit_return(self, node):
        pass

    def visit_continue(self, node):
        pass

    def visit_read(self, node):
        pass

    def visit_print(self, node):
        pass

    def visit_call(self, node):
        pass


    # ---------- Expressões ----------
    # Devolvem tipicamente (nó_possivelmente_reescrito_e_anotado).
    # O tipo deve ser anexado como último elemento do tuplo, na forma
    # de um dict {'type': 'integer'|'real'|'logical'|'string'}.
    def visit_num(self, node):
        pass

    def visit_bool(self, node):
        pass

    def visit_string(self, node):
        pass

    def visit_var(self, node):
        pass

    # Resolve a ambiguidade da gramática do fortran 77: ('call_or_array', NOME, args)
    # passa a ('call', NOME, args) ou ('index', NOME, args) consoante
    # o que estiver na tabela.
    def visit_call_or_array(self, node):
        pass

    def visit_index(self, node):
        pass

    def visit_binop(self, node):
        pass

    def visit_unop(self, node):
        pass

    def visit_relop(self, node):
        pass

    def visit_logop(self, node):
        pass

    def visit_not(self, node):
        pass


    # =====================================================================
    # PÓS-VALIDAÇÃO
    # Corre depois da passagem 2 dentro de cada program unit. Verifica que
    # cada GOTO/DO referenciado tem destino válido na program unit.
    # =====================================================================
    def _validate_labels(self):
        pass
