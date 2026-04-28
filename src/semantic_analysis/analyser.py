from semantic_analysis.symbol_table import Symbol, SymbolTable
from semantic_analysis.semantic_errors import SemanticErrorReporter, SemanticError
from semantic_analysis.builtins import register_builtins
from semantic_analysis.type_rules import (
    result_type_arith,
    result_type_unary_arith,
    result_type_logic,
    result_type_unary_logic,
    result_type_relop,
    compatible_assign,
    is_condition_type,
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
        self.referenced_labels = []       # [(label, line)] usadas em GOTO/DO no scope corrente
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
        # ('function', return_type_or_None, name, params_names, body)
        _, return_type, name, params, _ = node
        try:
            self.table.declare(Symbol(
                name=name,
                type=return_type,
                kind='function',
                # 'params' guarda a aridade (lista de tipos por preencher);
                # os tipos só ficam definitivos após visitar as declarações
                # do corpo da função na passagem 2.
                params=[None] * len(params),
            ))
        except SemanticError as e:
            self.reporter.errors.append(e)
            print(e.formatted())

    def _declare_subroutine(self, node):
        # ('subroutine', name, params_names, body)
        _, name, params, _ = node
        try:
            self.table.declare(Symbol(
                name=name,
                type=None,
                kind='subroutine',
                params=[None] * len(params),
            ))
        except SemanticError as e:
            self.reporter.errors.append(e)
            print(e.formatted())


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

    # Devolve o tipo anotado de um nó-expressão. Convencionamos que toda a
    # expressão visitada termina com {'type': ...} no último elemento.
    def _type_of(self, expr):
        if isinstance(expr, tuple) and len(expr) >= 1:
            last = expr[-1]
            if isinstance(last, dict) and 'type' in last:
                return last['type']
        return None


    # ---------- Program units ----------

    def visit_program(self, node):
        # ('program', [lista_de_unidades])
        tag, units = node
        annotated_units = [self.visit(u) for u in units]
        return (tag, annotated_units)


    def visit_main_program(self, node):
        # ('main_program', NOME, body)
        tag, name, body = node

        self.table.push_scope(name=name)
        self.referenced_labels = []

        annotated_body = self.visit(body)
        self._validate_labels()

        self.table.pop_scope()
        return (tag, name, annotated_body)

    def visit_function(self, node):
        # ('function', return_type, name, params_names, body)
        tag, return_type, name, params, body = node

        self.current_function = name
        self.table.push_scope(name=name)
        self.referenced_labels = []

        # Parâmetros declarados no scope local (tipo ainda desconhecido).
        for arg in params:
            try:
                self.table.declare(Symbol(name=arg, type=None, kind='param', initialized=True))
            except SemanticError as e:
                self.reporter.errors.append(e)
                print(e.formatted())

        # O nome da função vive também no scope local como variável do tipo
        # de retorno — em Fortran 77, atribuir ao nome da função define o
        # valor de retorno (ex: 'CONVRT = VAL').
        try:
            self.table.declare(Symbol(name=name, type=return_type, kind='var'))
        except SemanticError:
            pass

        annotated_body = self.visit(body)

        # Sincroniza tipos dos parâmetros para o símbolo global após declarações.
        # Tem de ser lookup_global: localmente o nome da função existe como
        # 'var' (para o valor de retorno) e iria fazer shadow.
        global_sym = self.table.lookup_global(name)
        if global_sym and global_sym.kind == 'function':
            global_sym.params = [
                self.table.lookup_local(p).type if self.table.lookup_local(p) else None
                for p in params
            ]
            local_self = self.table.lookup_local(name)
            if local_self and local_self.type and not global_sym.type:
                global_sym.type = local_self.type

        self._validate_labels()
        self.table.pop_scope()
        self.current_function = None
        return (tag, return_type, name, params, annotated_body)

    def visit_subroutine(self, node):
        # ('subroutine', name, params_names, body)
        tag, name, params, body = node

        self.table.push_scope(name=name)
        self.referenced_labels = []

        for arg in params:
            try:
                self.table.declare(Symbol(name=arg, type=None, kind='param', initialized=True))
            except SemanticError as e:
                self.reporter.errors.append(e)
                print(e.formatted())

        annotated_body = self.visit(body)

        global_sym = self.table.lookup_global(name)
        if global_sym and global_sym.kind == 'subroutine':
            global_sym.params = [
                self.table.lookup_local(p).type if self.table.lookup_local(p) else None
                for p in params
            ]

        self._validate_labels()
        self.table.pop_scope()
        return (tag, name, params, annotated_body)


    def visit_body(self, node):
        # ('body', [lista_de_declaracoes_e_statements])
        tag, statements = node
        annotated = [self.visit(s) for s in statements]
        return (tag, annotated)


    # ---------- Declarações ----------
    def visit_decl(self, node):
        # ('decl', 'integer', [('var_decl', 'N'), ('array_decl', 'NUMS', 10)])
        tag, var_type, decls = node

        for dec in decls:
            dec_tag = dec[0]
            dec_name = dec[1]

            existing = self.table.lookup_local(dec_name)

            # Forward declaration do tipo de retorno de uma função externa:
            # 'INTEGER CONVRT' no main, quando CONVRT é uma function global.
            # Não cria variável local — apenas confirma o tipo.
            if existing is None and dec_tag == 'var_decl':
                global_sym = self.table.lookup_global(dec_name)
                if global_sym and global_sym.kind == 'function':
                    if global_sym.type is None:
                        global_sym.type = var_type
                    elif global_sym.type != var_type:
                        raise SemanticError(
                            f"Tipo declarado ('{var_type}') não coincide com tipo de retorno de '{dec_name}' ('{global_sym.type}')"
                        )
                    continue

            if existing:
                # Promoção de parâmetro a tipo concreto, ou de variável
                # implícita (nome da função) ao tipo declarado.
                if existing.kind in ('param', 'var') and existing.type is None:
                    existing.type = var_type
                    if dec_tag == 'array_decl':
                        existing.kind = 'array'
                        existing.size = dec[2]
                elif existing.kind == 'var' and existing.type == var_type and dec_name == self.current_function:
                    # Redeclaração do nome da função com o mesmo tipo: aceita.
                    pass
                else:
                    raise SemanticError(
                        f"Variável '{dec_name}' já declarada neste scope"
                    )
            else:
                if dec_tag == 'var_decl':
                    self.table.declare(Symbol(name=dec_name, type=var_type, kind='var'))
                elif dec_tag == 'array_decl':
                    size = dec[2]
                    self.table.declare(Symbol(name=dec_name, type=var_type, kind='array', size=size))

        return node


    # ---------- Statements ----------
    def visit_labeled(self, node):
        # ('labeled', N, stmt_simples)
        tag, label, stmt = node
        try:
            self.table.declare_label(label, stmt[0])
        except SemanticError as e:
            self.reporter.errors.append(e)
            print(e.formatted())
        return (tag, label, self.visit(stmt))

    def visit_assign(self, node):
        # ('assign', target, expr) onde target é ('var', NAME) ou ('index', NAME, args)
        tag, target, expr = node
        expr_v = self.visit(expr)
        target_v, target_type = self._resolve_assign_target(target)
        value_type = self._type_of(expr_v)

        if target_type and value_type and not compatible_assign(target_type, value_type):
            raise SemanticError(
                f"Atribuição incompatível: {target_type} := {value_type}"
            )
        return (tag, target_v, expr_v)

    def _resolve_assign_target(self, target):
        if target[0] == 'var':
            name = target[1]
            sym = self.table.lookup(name)
            if sym.kind == 'array':
                raise SemanticError(
                    f"'{name}' é um array — falta o índice na atribuição"
                )
            if sym.kind in ('function', 'subroutine'):
                # Atribuir ao nome de função/subrotina só é válido se for a
                # função actual (em Fortran 77 essa é a forma de devolver valor).
                if sym.kind == 'function' and name == self.current_function:
                    self.table.initialize(name)
                    return (target, sym.type)
                raise SemanticError(
                    f"Não é possível atribuir a '{name}' (é {sym.kind})"
                )
            self.table.initialize(name)
            return (target, sym.type)

        if target[0] == 'index':
            _, name, args = target
            sym = self.table.lookup(name)
            if sym.kind != 'array':
                raise SemanticError(f"'{name}' não é um array; não pode ser indexado")
            if len(args) != 1:
                raise SemanticError(
                    f"Array '{name}' espera 1 índice, recebeu {len(args)}"
                )
            arg_v = self.visit(args[0])
            if not is_index_type(self._type_of(arg_v)):
                raise SemanticError(f"Índice de array '{name}' tem de ser integer")
            return (('index', name, [arg_v]), sym.type)

        raise SemanticError(f"Alvo de atribuição inválido: {target}")

    def visit_if_logico(self, node):
        # ('if_logico', cond, stmt)
        tag, cond, stmt = node
        cond_v = self.visit(cond)
        if not is_condition_type(self._type_of(cond_v)):
            raise SemanticError("Condição do IF tem de ser logical")
        return (tag, cond_v, self.visit(stmt))

    def visit_if_then(self, node):
        # ('if_then', cond, [stmts], [])
        tag, cond, stmts, _ = node
        cond_v = self.visit(cond)
        if not is_condition_type(self._type_of(cond_v)):
            raise SemanticError("Condição do IF tem de ser logical")
        body = [self.visit(s) for s in stmts]
        return (tag, cond_v, body, [])

    def visit_if_then_else(self, node):
        # ('if_then_else', cond, [then], [else])
        tag, cond, then_stmts, else_stmts = node
        cond_v = self.visit(cond)
        if not is_condition_type(self._type_of(cond_v)):
            raise SemanticError("Condição do IF tem de ser logical")
        then_b = [self.visit(s) for s in then_stmts]
        else_b = [self.visit(s) for s in else_stmts]
        return (tag, cond_v, then_b, else_b)

    def visit_do(self, node):
        # ('do', label_alvo, var_name, expr_inicio, expr_fim, expr_step_or_None)
        tag, label, var_name, e_ini, e_fim, e_step = node
        sym = self.table.lookup(var_name)
        if sym.kind not in ('var', 'param'):
            raise SemanticError(f"Variável de DO inválida: '{var_name}'")
        if not is_index_type(sym.type):
            raise SemanticError(f"Variável de DO '{var_name}' tem de ser integer")
        self.table.initialize(var_name)

        ini_v  = self.visit(e_ini)
        fim_v  = self.visit(e_fim)
        step_v = self.visit(e_step) if e_step is not None else None

        for expr_v, who in ((ini_v, 'inicial'), (fim_v, 'final')):
            t = self._type_of(expr_v)
            if not is_numeric_type(t):
                raise SemanticError(f"Limite {who} do DO tem de ser numérico")
        if step_v is not None and not is_numeric_type(self._type_of(step_v)):
            raise SemanticError("Passo do DO tem de ser numérico")

        self.referenced_labels.append((label, None))
        return (tag, label, var_name, ini_v, fim_v, step_v)

    def visit_goto(self, node):
        # ('goto', N)
        _, label = node
        self.referenced_labels.append((label, None))
        return node

    def visit_return(self, node):
        return node

    def visit_continue(self, node):
        return node

    def visit_read(self, node):
        # ('read', [itens])
        tag, items = node
        return (tag, [self._visit_io_target(it) for it in items])

    def _visit_io_target(self, it):
        # READ aceita variáveis simples ou elementos de array como destino.
        if isinstance(it, tuple) and it[0] == 'var':
            name = it[1]
            sym = self.table.lookup(name)
            if sym.kind == 'array':
                raise SemanticError(f"READ em '{name}' (array) — falta o índice")
            if sym.kind not in ('var', 'param'):
                raise SemanticError(f"READ destino inválido: '{name}'")
            self.table.initialize(name)
            return ('var', name, {'type': sym.type})

        if isinstance(it, tuple) and it[0] == 'call_or_array':
            _, name, args = it
            sym = self.table.lookup(name)
            if sym.kind != 'array':
                raise SemanticError(f"READ em '{name}': só variáveis e elementos de array")
            if len(args) != 1:
                raise SemanticError(f"Array '{name}' espera 1 índice")
            arg_v = self.visit(args[0])
            if not is_index_type(self._type_of(arg_v)):
                raise SemanticError(f"Índice de array '{name}' tem de ser integer")
            return ('index', name, [arg_v], {'type': sym.type})

        raise SemanticError("Item de READ tem de ser variável ou elemento de array")

    def visit_print(self, node):
        # ('print', [itens])
        tag, items = node
        return (tag, [self.visit(i) for i in items])

    def visit_call(self, node):
        # ('call', NOME, args) — vinda do CALL statement (subrotina).
        tag, name, args = node
        sym = self.table.lookup(name)
        if sym.kind not in ('subroutine', 'function'):
            raise SemanticError(f"'{name}' não é subrotina nem função")
        args_v = [self.visit(a) for a in args]
        expected = len(sym.params or [])
        if len(args_v) != expected:
            raise SemanticError(
                f"'{name}' espera {expected} arg(s), recebeu {len(args_v)}"
            )
        return (tag, name, args_v)


    # ---------- Expressões ----------
    # Devolvem (nó_anotado_com_dict_de_tipo_no_fim).
    def visit_num(self, node):
        # ('num', 10) ou ('num', 3.14)
        tag, value = node
        val_type = 'real' if isinstance(value, float) else 'integer'
        return (tag, value, {'type': val_type})

    def visit_var(self, node):
        # ('var', 'N')
        tag, name = node
        symbol = self.table.lookup(name)
        if symbol.kind in ('function', 'subroutine'):
            # Uso do nome como valor: só legal se for o nome da função actual
            # (referência ao "valor de retorno" antes de RETURN).
            if symbol.kind == 'function' and name == self.current_function:
                return (tag, name, {'type': symbol.type})
            raise SemanticError(
                f"'{name}' é {symbol.kind} e não pode ser usado como variável"
            )
        if symbol.kind == 'var' and not symbol.initialized and name != self.current_function:
            self.reporter.report(f"Variável '{name}' usada sem ter sido inicializada")
        return (tag, name, {'type': symbol.type})

    def visit_bool(self, node):
        # ('bool', True/False)
        tag, value = node
        return (tag, value, {'type': 'logical'})

    def visit_string(self, node):
        # ('string', 'valor')
        tag, value = node
        return (tag, value, {'type': 'string'})

    # Resolve a ambiguidade da gramática do Fortran 77:
    # ('call_or_array', NOME, args) → ('call', ...) ou ('index', ...) consoante
    # o que estiver na tabela de símbolos.
    def visit_call_or_array(self, node):
        _, name, args = node
        symbol = self.table.lookup(name)
        annotated_args = [self.visit(arg) for arg in args]

        if symbol.kind == 'function':
            expected = len(symbol.params or [])
            if len(annotated_args) != expected:
                raise SemanticError(
                    f"Função '{name}' espera {expected} arg(s), recebeu {len(annotated_args)}"
                )
            return ('call', name, annotated_args, {'type': symbol.type})

        if symbol.kind == 'array':
            if len(annotated_args) != 1:
                raise SemanticError(
                    f"Array '{name}' espera 1 índice, recebeu {len(annotated_args)}"
                )
            arg_type = self._type_of(annotated_args[0])
            if not is_index_type(arg_type):
                raise SemanticError(
                    f"Índice do array '{name}' tem de ser 'integer', mas recebeu '{arg_type}'"
                )
            return ('index', name, annotated_args, {'type': symbol.type})

        raise SemanticError(
            f"'{name}' não é função nem array — não pode ser chamado/indexado"
        )

    def visit_index(self, node):
        # Pode aparecer já anotado pelo parser (atribuição a array).
        _, name, args = node
        sym = self.table.lookup(name)
        if sym.kind != 'array':
            raise SemanticError(f"'{name}' não é array")
        if len(args) != 1:
            raise SemanticError(f"Array '{name}' espera 1 índice")
        arg_v = self.visit(args[0])
        if not is_index_type(self._type_of(arg_v)):
            raise SemanticError(f"Índice de array '{name}' tem de ser integer")
        return ('index', name, [arg_v], {'type': sym.type})

    def visit_binop(self, node):
        # ('binop', '+', left, right)
        tag, op, left, right = node
        l = self.visit(left)
        r = self.visit(right)
        t = result_type_arith(self._type_of(l), op, self._type_of(r))
        if t is None:
            raise SemanticError(
                f"Operação '{op}' inválida entre '{self._type_of(l)}' e '{self._type_of(r)}'"
            )
        return (tag, op, l, r, {'type': t})

    def visit_unop(self, node):
        # ('unop', '-', expr)
        tag, op, expr = node
        e = self.visit(expr)
        t = result_type_unary_arith(self._type_of(e))
        if t is None:
            raise SemanticError(
                f"Operador unário '{op}' não pode ser aplicado a '{self._type_of(e)}'"
            )
        return (tag, op, e, {'type': t})

    def visit_relop(self, node):
        # ('relop', '.GT.', left, right)
        tag, op, left, right = node
        l = self.visit(left)
        r = self.visit(right)
        t = result_type_relop(self._type_of(l), op, self._type_of(r))
        if t is None:
            raise SemanticError(
                f"Comparação '{op}' inválida entre '{self._type_of(l)}' e '{self._type_of(r)}'"
            )
        return (tag, op, l, r, {'type': t})

    def visit_logop(self, node):
        # ('logop', 'and'/'or', left, right)
        tag, op, left, right = node
        l = self.visit(left)
        r = self.visit(right)
        t = result_type_logic(self._type_of(l), op, self._type_of(r))
        if t is None:
            raise SemanticError(
                f"Operador lógico '{op}' exige operandos logical"
            )
        return (tag, op, l, r, {'type': t})

    def visit_not(self, node):
        # ('not', expr)
        tag, expr = node
        e = self.visit(expr)
        t = result_type_unary_logic(self._type_of(e))
        if t is None:
            raise SemanticError(".NOT. exige operando logical")
        return (tag, e, {'type': t})


    # =====================================================================
    # PÓS-VALIDAÇÃO
    # Corre depois da passagem 2 dentro de cada program unit. Verifica que
    # cada GOTO/DO referenciado tem destino válido na program unit.
    # =====================================================================
    def _validate_labels(self):
        for label, line in self.referenced_labels:
            if self.table.lookup_label(label) is None:
                self.reporter.report(
                    f"Label {label} referenciada mas não definida",
                    line,
                )
        self.referenced_labels = []
