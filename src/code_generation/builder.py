from code_generation import ir
from code_generation.layout import GlobalLayout, LocalLayout
from semantic_analysis.builtins import BUILTINS


# Tradução AST anotada → IR linear.
#
# Cobre o programa principal, funções e subrotinas do utilizador, bem como
# funções intrínsecas via tabela de built-ins. As program units do utilizador
# são emitidas após o HALT do main, sob labels com o nome da função/subrotina.


# Conjunto de nomes de built-ins (validar rapidamente se um 'call' é nativo
# ou definido pelo utilizador).
_BUILTIN_NAMES = {b[0] for b in BUILTINS}


class IRBuilder:
    def __init__(self, table):
        self.table   = table        # tabela de símbolos (do analyser)
        self.layout  = GlobalLayout()
        self.code    = []           # lista de instruções IR
        self._lblcnt = 0
        self._current_local = None    # LocalLayout activo, None no main
        self._current_n_locals = 0    # tamanho do frame local activo

    # Identificador único para labels geradas pelo compilador (IF, DO, ...).
    # Labels do programador (10, 20, ...) são reusadas tal como vêm na AST,
    # com prefixo 'L' para evitar colisão com nomes auto-gerados.
    def _new_label(self, hint='L'):
        self._lblcnt += 1
        return f"{hint}{self._lblcnt}"

    def _user_label(self, n):
        return f"L{n}"

    # Entry point. Devolve a lista de instruções IR.
    def build(self, ast):
        # 1. Programa principal vem primeiro, terminado por HALT.
        for unit in ast[1]:
            if unit[0] == 'main_program':
                self._emit_main(unit)
        self.code.append(ir.HALT())

        # 2. Subprogramas após o HALT — só executam quando chamados via CALL.
        for unit in ast[1]:
            if unit[0] == 'function':
                self._emit_function(unit)
            elif unit[0] == 'subroutine':
                self._emit_subroutine(unit)

        return self.code, self.layout

    def _emit(self, instr):
        self.code.append(instr)

    # ---------- Acesso a variáveis (scope-aware) ----------
    # Decidem global vs local consoante o scope ativo. Usa-se em todas as
    # leituras/escritas de variáveis simples e em arrays (indexados).

    def _emit_load_var(self, name, type_):
        if self._current_local is not None and name in self._current_local:
            self._emit(ir.LOADL(name, type_, self._current_local.of(name)))
        else:
            self._emit(ir.LOAD(name, type_))

    def _emit_store_var(self, name, type_):
        if self._current_local is not None and name in self._current_local:
            self._emit(ir.STOREL(name, type_, self._current_local.of(name)))
        else:
            self._emit(ir.STORE(name, type_))

    def _scope_type(self, name):
        if self._current_local is not None and name in self._current_local:
            return self._current_local.type.get(name)
        if name in self.layout.type:
            return self.layout.type[name]
        sym = self.table.lookup_global(name)
        return sym.type if sym else None

    # ---------- Main program ----------
    def _emit_main(self, node):
        # ('main_program', NAME, body)
        _, _, body = node

        # Recolhe declarações antes de gerar código de statements: a EWVM
        # exige que reservemos os slots globais no início do programa.
        self._collect_globals_from_body(body)
        self._emit_globals_init()

        # Statements em ordem.
        for it in body[1]:
            if it[0] == 'decl':
                continue   # já processadas em _collect_globals_from_body
            self._emit_stmt(it)

    def _collect_globals_from_body(self, body):
        for it in body[1]:
            if it[0] == 'decl':
                _, type_, decls = it
                for d in decls:
                    name = d[1]
                    # Forward-decl do tipo de retorno de uma função externa
                    # (ex: 'INTEGER CONVRT' no main): não reservar slot global.
                    sym = self.table.lookup_global(name)
                    if sym and sym.kind in ('function', 'subroutine'):
                        continue
                    if d[0] == 'var_decl':
                        self.layout.allocate(name, 'var', type=type_)
                    elif d[0] == 'array_decl':
                        self.layout.allocate(name, 'array', arr_size=d[2], type=type_)

    def _emit_globals_init(self):
        # Reserva espaço inicializado a 0 para todas as variáveis/arrays.
        for name, off in sorted(self.layout.offset.items(), key=lambda kv: kv[1]):
            n     = self.layout.size[name]
            type_ = self.layout.type.get(name) or 'integer'
            zero  = 0.0 if type_ == 'real' else 0
            for _ in range(n):
                self._emit(ir.CONST(zero, type_))

    # ---------- Subprogramas ----------
    def _emit_function(self, node):
        # ('function', return_type, name, params, body)
        _, ret_type, name, params, body = node
        local = LocalLayout(n_args=len(params), has_retval=True)

        # Parâmetros (índices 1..N).
        param_types = self._param_types_for(name)
        for i, p in enumerate(params, start=1):
            ptype = param_types[i - 1] if i - 1 < len(param_types) else None
            local.allocate_param(p, i, ptype or 'integer')
        # Slot de retorno: tem o nome da função.
        local.allocate_retval(name, ret_type or 'integer')
        # Locais regulares (declarações no corpo, excluindo params e nome).
        self._collect_locals_from_body(body, local, exclude={name, *params})

        self._emit(ir.LABEL(name))
        n_locals = local.total_locals()
        if n_locals > 0:
            self._emit(ir.PUSHN(n_locals))

        prev_local = self._current_local
        prev_n_locals = self._current_n_locals
        self._current_local = local
        self._current_n_locals = n_locals
        for it in body[1]:
            if it[0] == 'decl':
                continue
            self._emit_stmt(it)
        # RETURN final defensivo (caso a função não termine explicitamente).
        if not self.code or self.code[-1][0] != 'RETURN':
            self._emit_subprog_return()
        self._current_local = prev_local
        self._current_n_locals = prev_n_locals

    def _emit_subroutine(self, node):
        # ('subroutine', name, params, body)
        _, name, params, body = node
        local = LocalLayout(n_args=len(params), has_retval=False)

        param_types = self._param_types_for(name)
        for i, p in enumerate(params, start=1):
            ptype = param_types[i - 1] if i - 1 < len(param_types) else None
            local.allocate_param(p, i, ptype or 'integer')
        self._collect_locals_from_body(body, local, exclude=set(params))

        self._emit(ir.LABEL(name))
        n_locals = local.total_locals()
        if n_locals > 0:
            self._emit(ir.PUSHN(n_locals))

        prev_local = self._current_local
        prev_n_locals = self._current_n_locals
        self._current_local = local
        self._current_n_locals = n_locals
        for it in body[1]:
            if it[0] == 'decl':
                continue
            self._emit_stmt(it)
        if not self.code or self.code[-1][0] != 'RETURN':
            self._emit_subprog_return()
        self._current_local = prev_local
        self._current_n_locals = prev_n_locals

    # Em subprogramas com locais, descartamos explicitamente o frame antes
    # de RETURN. A documentação da EWVM diz que RETURN faz sp = fp (que já
    # devolveria o espaço dos locais), mas a implementação observada não
    # cumpre isso — sem este POPN, a stack acumula 'lixo' por chamada e o
    # caller acaba a ler valores errados depois do CALL.
    def _emit_subprog_return(self):
        if self._current_n_locals > 0:
            self._emit(ir.POPN(self._current_n_locals))
        self._emit(ir.RETURN())

    def _collect_locals_from_body(self, body, local, exclude):
        for it in body[1]:
            if it[0] != 'decl':
                continue
            _, type_, decls = it
            for d in decls:
                name = d[1]
                if name in exclude:
                    # Mesmo se aparecer numa declaração (ex: 'INTEGER N, B'
                    # para tipar parâmetros), o slot já existe.
                    if name in local.offset and local.type.get(name) is None:
                        local.type[name] = type_
                    continue
                if d[0] == 'var_decl':
                    local.allocate_local(name, kind='var', type=type_)
                elif d[0] == 'array_decl':
                    local.allocate_local(name, kind='array', arr_size=d[2], type=type_)

    def _param_types_for(self, fn_name):
        sym = self.table.lookup_global(fn_name)
        return list(sym.params) if sym and sym.params else []

    # ---------- Statements ----------
    def _emit_stmt(self, node):
        tag = node[0]
        method = getattr(self, f'_stmt_{tag}', None)
        if method is None:
            raise NotImplementedError(f"Statement não suportado: {tag}")
        method(node)

    def _stmt_labeled(self, node):
        # ('labeled', N, stmt)
        _, label_n, inner = node
        self._emit(ir.LABEL(self._user_label(label_n)))
        self._emit_stmt(inner)

    def _stmt_assign(self, node):
        # ('assign', target, expr)
        _, target, expr = node
        target_type = self._target_type(target)
        self._emit_expr(expr, expected_type=target_type)
        if target[0] == 'var':
            self._emit_store_var(target[1], target_type)
        elif target[0] == 'index':
            # target = ('index', NAME, [arg])  ou já anotado
            name = target[1]
            args = target[2]
            self._emit_expr(args[0], expected_type='integer')
            self._emit(ir.STOREIDX(name, target_type))

    def _target_type(self, target):
        # Atribuições produzidas pelo analyser não anotam o LHS; vamos à
        # tabela buscar o tipo.
        if target[0] in ('var', 'index'):
            return self._sym_type(target[1])
        return None

    def _sym_type(self, name):
        # Tipo da variável: primeiro consulta o scope corrente (local), depois
        # globais, depois símbolos globais (funções/subrotinas).
        return self._scope_type(name)

    def _stmt_if_logico(self, node):
        # ('if_logico', cond, stmt) — IF (cond) stmt
        _, cond, stmt = node
        L_end = self._new_label('IFEND')
        self._emit_expr(cond, expected_type='logical')
        self._emit(ir.JZ(L_end))
        self._emit_stmt(stmt)
        self._emit(ir.LABEL(L_end))

    def _stmt_if_then(self, node):
        # ('if_then', cond, [stmts], [])
        _, cond, stmts, _ = node
        L_end = self._new_label('IFEND')
        self._emit_expr(cond, expected_type='logical')
        self._emit(ir.JZ(L_end))
        for s in stmts:
            self._emit_stmt(s)
        self._emit(ir.LABEL(L_end))

    def _stmt_if_then_else(self, node):
        # ('if_then_else', cond, [then], [else])
        _, cond, then_b, else_b = node
        L_else = self._new_label('IFELSE')
        L_end  = self._new_label('IFEND')
        self._emit_expr(cond, expected_type='logical')
        self._emit(ir.JZ(L_else))
        for s in then_b:
            self._emit_stmt(s)
        self._emit(ir.JUMP(L_end))
        self._emit(ir.LABEL(L_else))
        for s in else_b:
            self._emit_stmt(s)
        self._emit(ir.LABEL(L_end))

    def _stmt_do(self, node):
        # ('do', label_alvo, var_name, e_ini, e_fim, e_step_or_None)
        # Em Fortran 77, o corpo é a sequência de statements até à label_alvo
        # (inclusive). Aqui só geramos o cabeçalho; o corpo é emitido pelos
        # statements seguintes. O CONTINUE/labeled fecha o ciclo.
        _, target_label, var_name, e_ini, e_fim, e_step = node
        L_top  = self._new_label('DO')
        L_end  = self._new_label('DOEND')
        # Inicializa contador.
        self._emit_expr(e_ini, expected_type='integer')
        self._emit_store_var(var_name, 'integer')
        # Recalcula limite/passo a cada iteração — o optimizer pode depois
        # extrair invariantes para um temporário.
        self._emit(ir.LABEL(L_top))
        self._emit_load_var(var_name, 'integer')
        self._emit_expr(e_fim, expected_type='integer')
        self._emit(ir.RELOP('.LE.', 'integer'))
        self._emit(ir.JZ(L_end))

        # Empilha o cabeçalho do DO numa pilha interna para o CONTINUE/labeled
        # saber onde continuar e onde terminar.
        self._do_stack.append((target_label, var_name, e_step, L_top, L_end))

    def _stmt_continue(self, node):
        # CONTINUE só faz sentido como destino de DO. Quando aparece como
        # ('labeled', N, ('continue',)) e N é o destino do DO no topo, fecha
        # o ciclo: incrementa var, salta para o topo, marca L_end.
        if self._do_stack and self._do_stack[-1][0] is None:
            # CONTINUE solto — equivale a no-op (raro em Fortran 77 standard).
            return
        # CONTINUE solto sem DO associado: gera nada.
        return

    def _stmt_goto(self, node):
        _, label_n = node
        self._emit(ir.JUMP(self._user_label(label_n)))

    def _stmt_return(self, node):
        # No main program é HALT; em subprogramas, descarta locais e RETURN.
        if self._current_local is None:
            self._emit(ir.HALT())
        else:
            self._emit_subprog_return()

    def _stmt_call(self, node):
        # ('call', NAME, [args_anotados]) — chamada a SUBROUTINE.
        _, name, args = node
        param_types = self._param_types_for(name)
        for i, a in enumerate(args):
            expected = param_types[i] if i < len(param_types) else None
            self._emit_expr(a, expected_type=expected)
        self._emit(ir.PUSHA(name))
        self._emit(ir.CALL_USER(name, len(args), False))
        if len(args) > 0:
            self._emit(ir.POPN(len(args)))

    def _stmt_read(self, node):
        # ('read', [items])
        _, items = node
        for it in items:
            tag = it[0]
            if tag == 'var':
                # ('var', NAME, {type}) após análise semântica
                name = it[1]
                type_ = self._extract_type(it) or self._sym_type(name) or 'integer'
                self._emit(ir.READ(type_, name))
                self._emit_store_var(name, type_)
            elif tag == 'index':
                # ('index', NAME, [arg], {type})
                name = it[1]
                args = it[2]
                type_ = self._extract_type(it) or self._sym_type(name) or 'integer'
                self._emit(ir.READ(type_, name))
                self._emit_expr(args[0], expected_type='integer')
                self._emit(ir.STOREIDX(name, type_))
            else:
                raise NotImplementedError(f"READ destino: {tag}")

    def _stmt_print(self, node):
        # ('print', [items]) — Fortran 77 separa items por espaço.
        _, items = node
        for i, it in enumerate(items):
            if i > 0:
                self._emit(ir.CONST(' ', 'string'))
                self._emit(ir.WRITE('string'))
            type_ = self._extract_type(it)
            if type_ == 'string':
                self._emit_expr(it, expected_type='string')
                self._emit(ir.WRITE('string'))
            else:
                self._emit_expr(it, expected_type=type_ or 'integer')
                self._emit(ir.WRITE(type_ or 'integer'))
        self._emit(ir.WRITELN())

    # Inicializado lazy para permitir aninhamento simples de DOs.
    @property
    def _do_stack(self):
        if not hasattr(self, '_do_stk'):
            self._do_stk = []
        return self._do_stk

    # No final do statement labelled, se a label corresponder ao destino de
    # um DO no topo da pilha, fechamos o ciclo. Para isso, o _stmt_labeled
    # precisa de saber. Reescreve-se abaixo.
    def _close_do_if_target(self, label_n):
        if not self._do_stack:
            return False
        target, var_name, e_step, L_top, L_end = self._do_stack[-1]
        if target != label_n:
            return False
        # Incrementa var pelo step (default 1).
        self._emit_load_var(var_name, 'integer')
        if e_step is None:
            self._emit(ir.CONST(1, 'integer'))
        else:
            self._emit_expr(e_step, expected_type='integer')
        self._emit(ir.BINOP('+', 'integer'))
        self._emit_store_var(var_name, 'integer')
        self._emit(ir.JUMP(L_top))
        self._emit(ir.LABEL(L_end))
        self._do_stack.pop()
        return True


    # ---------- Expressões ----------
    # 'expected_type' permite-nos inserir promoções automáticas integer→real
    # quando o LHS é real e a expressão é integer (ou um operando da soma é).
    def _emit_expr(self, node, expected_type=None):
        tag = node[0]
        method = getattr(self, f'_expr_{tag}', None)
        if method is None:
            raise NotImplementedError(f"Expressão não suportada: {tag}")
        actual = method(node)
        # Promoção integer → real se necessário.
        if expected_type == 'real' and actual == 'integer':
            self._emit(ir.I2F())
            actual = 'real'
        return actual

    def _expr_num(self, node):
        # ('num', value, {type})
        _, v, meta = node
        t = meta['type']
        self._emit(ir.CONST(v, t))
        return t

    def _expr_bool(self, node):
        _, v, _meta = node
        self._emit(ir.CONST(1 if v else 0, 'logical'))
        return 'logical'

    def _expr_string(self, node):
        _, s, _meta = node
        self._emit(ir.CONST(s, 'string'))
        return 'string'

    def _expr_var(self, node):
        # ('var', NAME, {type})
        _, name, meta = node
        t = meta['type']
        self._emit_load_var(name, t)
        return t

    def _expr_index(self, node):
        # ('index', NAME, [arg], {type})
        _, name, args, meta = node
        t = meta['type']
        self._emit_expr(args[0], expected_type='integer')
        self._emit(ir.LOADIDX(name, t))
        return t

    def _expr_call(self, node):
        # ('call', NAME, [args_anotados], {type}) — função intrínseca ou utilizador.
        _, name, args, meta = node
        ret_type = meta['type']
        if name in _BUILTIN_NAMES:
            for a in args:
                self._emit_expr(a)
            self._emit(ir.CALL_BUILTIN(name, len(args), ret_type))
            return ret_type

        # Função do utilizador: convenção de chamada com slot de retorno
        # alocado pelo caller imediatamente abaixo dos argumentos.
        zero = 0.0 if ret_type == 'real' else 0
        self._emit(ir.CONST(zero, ret_type))
        param_types = self._param_types_for(name)
        for i, a in enumerate(args):
            expected = param_types[i] if i < len(param_types) else None
            self._emit_expr(a, expected_type=expected)
        self._emit(ir.PUSHA(name))
        self._emit(ir.CALL_USER(name, len(args), True))
        if len(args) > 0:
            self._emit(ir.POPN(len(args)))
        return ret_type

    def _expr_binop(self, node):
        # ('binop', op, a, b, {type})
        _, op, a, b, meta = node
        result_t = meta['type']
        self._emit_expr(a, expected_type=result_t)
        self._emit_expr(b, expected_type=result_t)
        self._emit(ir.BINOP(op, result_t))
        return result_t

    def _expr_unop(self, node):
        # ('unop', op, a, {type})
        _, op, a, meta = node
        t = meta['type']
        self._emit_expr(a, expected_type=t)
        if op == '-':
            self._emit(ir.NEG(t))
        # '+' unário é no-op
        return t

    def _expr_relop(self, node):
        # ('relop', op, a, b, {type='logical'})
        _, op, a, b, _meta = node
        # Determina tipo dos operandos: se algum for real, promove ambos.
        ta = self._extract_type(a) or 'integer'
        tb = self._extract_type(b) or 'integer'
        operand_t = 'real' if (ta == 'real' or tb == 'real') else 'integer'
        self._emit_expr(a, expected_type=operand_t)
        self._emit_expr(b, expected_type=operand_t)
        self._emit(ir.RELOP(op, operand_t))
        return 'logical'

    def _expr_logop(self, node):
        # ('logop', op, a, b, {type='logical'})
        _, op, a, b, _meta = node
        self._emit_expr(a, expected_type='logical')
        self._emit_expr(b, expected_type='logical')
        self._emit(ir.LOGOP(op))
        return 'logical'

    def _expr_not(self, node):
        # ('not', a, {type='logical'})
        _, a, _meta = node
        self._emit_expr(a, expected_type='logical')
        self._emit(ir.NOT())
        return 'logical'

    # Helper: extrai o {'type': ...} do último elemento, se existir.
    def _extract_type(self, expr):
        if isinstance(expr, tuple) and len(expr) >= 1:
            last = expr[-1]
            if isinstance(last, dict) and 'type' in last:
                return last['type']
        return None


# Sobrepõe _stmt_labeled para fechar DO loops no fim do statement rotulado.
# (Definimos aqui para manter a função principal pequena; em Python podemos
# também adicionar via método normal — feito em monkey patch a seguir.)
def _stmt_labeled_with_do(self, node):
    _, label_n, inner = node
    self._emit(ir.LABEL(self._user_label(label_n)))
    self._emit_stmt(inner)
    # Se este label é alvo do DO actual, fecha-o.
    self._close_do_if_target(label_n)

IRBuilder._stmt_labeled = _stmt_labeled_with_do
