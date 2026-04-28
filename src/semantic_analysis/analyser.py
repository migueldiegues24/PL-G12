from semantic_analysis.symbol_table import Symbol, SymbolTable
from semantic_analysis.semantic_errors import SemanticErrorReporter, SemanticError
from semantic_analysis.builtins import register_builtins
from semantic_analysis.type_rules import (
    result_type_arith,
    result_type_logic,
    result_type_relop,
    compatible_assign,
    is_condition_type,
    result_type_unary_logic,
    is_numeric_type,
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
        self.referenced_labels = set()
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
            kind='function',
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
        new_elements = []
        
        for item in node:
            if isinstance(item, tuple):
                # nó filho da AST (ex: ('var', 'X')) -> visita recursiva
                new_elements.append(self.visit(item))
            elif isinstance(item, list):
                # lista de nós (ex: corpo do programa, lista de argumentos)
                visited_list = []
                for sub_item in item:
                    if isinstance(sub_item, tuple):
                        visited_list.append(self.visit(sub_item))
                    else:
                        visited_list.append(sub_item)
                new_elements.append(visited_list)
            else:
                # É um valor primitivo (a tag do nó, nome de variável, número de linha, etc.)
                new_elements.append(item)
                
        # Reconstrói o nó com as partes possivelmente anotadas/transformadas
        return tuple(new_elements)


    # ---------- Program units ----------
    
    def visit_program(self, node):
        #('program', [lista_de_unidades])
        tag, units = node
        
        annotated_units = []
        for unit in units:
            annotated_units.append(self.visit(unit))
            
        return (tag, annotated_units)


    def visit_main_program(self, node):
        # ('main_program', NOME, body)
        tag, name, body = node
        
        self.table.push_scope(name=name)
        
        # 2. Visitar o corpo (que vai processar as declarações e os statements)
        # Variáveis do main são guardadas no scope que acabámos de criar.
        annotated_body = self.visit(body)
        
        # 3. Correr as validações finais desta program unit
        # (ex: verificar se todos os 'goto 10' apontam para labels que realmente existem)
        self._validate_labels()
        
        # 4. Sair do scope local (limpa as variáveis locais para a próxima program unit)
        self.table.pop_scope()
        
        # Devolve o nó reconstruído
        return (tag, name, annotated_body)

    def visit_function(self, node):
        # ('function, return_type, tag(name), args, body)
        tag, return_type, name, args, body = node
        
        self.current_function = name
        
        self.table.push_scope(name=name)
        
        # Registar os parâmetros na tabela local ANTES de visitar o body.
        # (O tipo fica None por agora, será preenchido quando o visit_decl os encontrar)
        for arg in args:
            param_symbol = Symbol(name=arg, type=None, kind='param')
            self.table.declare(param_symbol)
        
        #Visitar o corpo da função
        annotated_body = self.visit(body)
        
        #Fazer as validações de labels
        self._validate_labels()
        
        #Sair do scope e limpar o contexto da função
        self.table.pop_scope()
        self.current_function = None
        
        #Devolver o nó reconstruído com a estrutura completa!
        return (tag, return_type, name, args, annotated_body)

    def visit_subroutine(self, node):
        # ('subroutine', name, args, body)
        tag, name, args, body = node
        
        self.table.push_scope(name=name)
        
        for arg in args:
            param_symbol = Symbol(name=arg, type=None, kind='param')
            self.table.declare(param_symbol)
        
        annotated_body = self.visit(body)
        
        self._validate_labels()
        
        self.table.pop_scope()
        
        return (tag, name, args, annotated_body)


    def visit_body(self, node):
        # ('body', [lista_de_declaracoes_e_statements])
        tag, statements = node
        
        annotated_statements = []
        for stmt in statements:
            annotated_statements.append(self.visit(stmt))
            
        return (tag, annotated_statements)


    # ---------- Declarações ----------
    def visit_decl(self, node):
        #('decl', 'integer', [('var_decl', 'N'), ('array_decl', 'NUMS', 10)])
        tag, var_type, decls = node
        
        for dec in decls:
            dec_tag = dec[0]
            dec_name = dec[1]
            
            existing_symbol = self.table.lookup_local(dec_name)
            
            if existing_symbol:
                if existing_symbol.kind == 'param':
                    existing_symbol.type = var_type
                    
                    if dec_tag == 'array_decl':
                        existing_symbol.kind = 'array'
                        existing_symbol.size = dec[2]
                else:
                    # Se não for parâmetro, o programador está a redeclarar uma variável local
                    raise SemanticError(f"Variável '{dec_name}' já foi declarada neste scope.")
            
            else:
                if dec_tag == 'var_decl':
                    new_symbol = Symbol(name=dec_name, type=var_type, kind='var')
                    
                elif dec_tag == 'array_decl':
                    size = dec[2] # O terceiro elemento é o tamanho do array
                    new_symbol = Symbol(name=dec_name, type=var_type, kind='array', size=size)
                
                self.table.declare(new_symbol)

        # Como os nós de declaração servem apenas para alimentar a Tabela de Símbolos,
        # não precisamos de os reescrever ou anotar. Podemos devolver o nó original tal como entrou.
        return node
            


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
        #  ('num', 10) ou ('num', 3.14)
        tag, value = node
        
        # Inferimos o tipo de Fortran com base no tipo do valor no Python
        if isinstance(value, float):
            val_type = 'real'
        else:
            val_type = 'integer'
            
        # Devolve o nó original MAIS o dicionário de anotação
        return (tag, value, {'type': val_type})


    def visit_var(self, node):
        # ('var', 'N')
        tag, name = node
        
        # Vai à tabela de símbolos garantir que a variável existe.
        # O método lookup já lança SemanticError se não encontrar.
        symbol = self.table.lookup(name)
        
        # Devolve o nó reconstruído com o tipo pendurado
        return (tag, name, {'type': symbol.type})

    def visit_bool(self, node):
        # ('bool', True) ou ('bool', False)
        tag, value = node
        
        return (tag, value, {'type': 'logical'})

    def visit_string(self, node):
        # ('string', 'valor')
        tag, value = node
        
        return (tag, value, {'type': 'string'})

    # Resolve a ambiguidade da gramática do fortran 77: ('call_or_array', NOME, args)
    # passa a ('call', NOME, args) ou ('index', NOME, args) consoante
    # o que estiver na tabela.
    def visit_call_or_array(self, node):
        # ('call_or_array', 'MOD', [('var', 'QUOT'), ('var', 'B')])
        tag, name, args = node
        
        # Procurar o símbolo na tabela
        # Se não existir, o lookup já dispara o SemanticError natural.
        symbol = self.table.lookup(name)
        
        # Visitar os argumentos independentemente do que for (função ou array)
        # Isto processa as variáveis/números lá dentro e pendura o {'type': ...} em cada um.
        annotated_args = [self.visit(arg) for arg in args]
        
        # Desambiguação baseada no 'kind' registado na Tabela de Símbolos
        if symbol.kind == 'function':
            # É uma chamada de função.
            # O tipo de retorno deste nó é o tipo da função (ex: 'integer' para MOD)
            return ('call', name, annotated_args, {'type': symbol.type})
            
        elif symbol.kind == 'array':
            # É um acesso a um array.
            # Validação: Em Fortran, todos os índices de arrays TÊM de ser 'integer'
            for i, arg in enumerate(annotated_args):
                arg_type = arg[-1]['type']
                if not is_index_type(arg_type):
                    raise SemanticError(
                        f"O índice {i+1} do array '{name}' tem de ser 'integer', mas recebeu '{arg_type}'."
                    )
            
            # O tipo deste nó é o tipo dos elementos do array.
            return ('index', name, annotated_args, {'type': symbol.type})
            
        else:
            # O programador tentou meter parênteses à frente de uma variável normal!
            # Exemplo: NUM = 10 \n PRINT, NUM(5)
            raise SemanticError(
                f"O identificador '{name}' está a ser usado com parênteses, mas foi declarado como '{symbol.kind}' (não é função nem array)."
            )

    def visit_binop(self, node):
        #  ('binop', '+', ('var', 'A'), ('num', 1))
        tag, op, left, right = node
        
        # Visitar os filhos para processar as expressões abaixo
        annotated_left = self.visit(left)
        annotated_right = self.visit(right)
        
        # Extrair os tipos dos filhos anotados
        type_left = annotated_left[-1]['type']
        type_right = annotated_right[-1]['type']
        
        # Validar a semântica da operação aritmética
        result_type = result_type_arith(type_left, op, type_right)
        
        if not result_type:
            raise SemanticError(
                f"Operação '{op}' inválida entre tipos '{type_left}' e '{type_right}'."
            )
            
        # Devolver o nó reconstruído com o tipo resultante da operação
        return (tag, op, annotated_left, annotated_right, {'type': result_type})

    def visit_unop(self, node):
        # ('unop', '-', ('var', 'X'))
        tag, op, expr = node
        
        # Visitar a expressão filha
        annotated_expr = self.visit(expr)
        
        # Extrair o tipo
        expr_type = annotated_expr[-1]['type']
        
        # Validar se a expressão é numérica
        if not is_numeric_type(expr_type):
            raise SemanticError(
                f"Operador unário '{op}' não pode ser aplicado ao tipo '{expr_type}'."
            )
            
        # Devolver o nó reconstruído (o tipo mantém-se)
        return (tag, op, annotated_expr, {'type': expr_type})

    def visit_relop(self, node):
        # ('relop', '.GT.', ('var', 'QUOT'), ('num', 0))
        tag, op, left, right = node
        
        annotated_left  = self.visit(left)
        annotated_right = self.visit(right)
        
        left_type   = annotated_left[-1]['type']
        right_type  = annotated_right[-1]['type']
        
        expr_type = result_type_relop(left_type,op,right_type)
        if not expr_type:
            raise SemanticError(
                f"Operador '{op}' não pode ser aplicado aos tipos da expressão: {left_type}, {right_type}"
            )
        return (tag, op, annotated_left, annotated_right, {'type': expr_type})

    def visit_logop(self, node):
        # ('logop', '.AND.', left_expr, right_expr)
        tag, op, left, right = node
        
        # Visitar os nós filhos
        annotated_left  = self.visit(left)
        annotated_right = self.visit(right)
        
        # Extrair os tipos
        left_type   = annotated_left[-1]['type']
        right_type  = annotated_right[-1]['type']
        
        # Validar a semântica (têm de ser ambos 'logical')
        expr_type = result_type_logic(left_type, op, right_type)
        
        if not expr_type:
            raise SemanticError(
                f"Operador lógico '{op}' não pode ser aplicado aos tipos da expressão: '{left_type}' e '{right_type}'."
            )
            
        # Devolver o nó anotado
        return (tag, op, annotated_left, annotated_right, {'type': expr_type})

    def visit_not(self, node):
        # ('not', expr)
        tag, expr = node
        
        annotated_expr = self.visit(expr)
        expr_type = annotated_expr[-1]['type']
        
        # Em Fortran, o .NOT. só pode ser aplicado a expressões lógicas)
        if expr_type != 'logical':
            raise SemanticError(
                f"Operador '.NOT.' exige o tipo 'logical', mas recebeu '{expr_type}'."
            )
            
        return (tag, annotated_expr, {'type': 'logical'})


    # =====================================================================
    # PÓS-VALIDAÇÃO
    # Corre depois da passagem 2 dentro de cada program unit. Verifica que
    # cada GOTO/DO referenciado tem destino válido na program unit.
    # =====================================================================
    def _validate_labels(self):
        # Percorre todas as labels que foram chamadas por GOTO ou DO nesta program unit
        for label in self.referenced_labels:
            # Se a label não existir no scope atual (não foi declarada por um 'labeled' statement)
            if not self.table.lookup_label(label):
                raise SemanticError(
                    f"A label '{label}' foi referenciada, mas não está definida nesta program unit."
                )
                
        # Limpa o set para que a próxima função/subrotina comece com o registo limpo
        self.referenced_labels.clear()
