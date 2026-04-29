from code_generation import ir


# Optimizador da IR.
#
# Cada pass é uma função  lista de instruções IR -> lista de instruções IR
# semanticamente equivalente. Os passes são ordenados de modo a abrirem
# oportunidades uns aos outros (constant folding produz CONST que activa
# algebraic simplification que pode tornar saltos triviais que jump_threading
# remove).
#
# Os passes são corridos em ponto-fixo (até nada mudar) para apanhar
# transformações em cascata.


def optimize(code, passes=None):
    if passes is None:
        passes = DEFAULT_PASSES
    changed = True
    while changed:
        changed = False
        for p in passes:
            new_code = p(code)
            if new_code != code:
                code = new_code
                changed = True
    return code


# ----------------------- Helpers -------------------------------------------

def _is_const(instr):
    return isinstance(instr, tuple) and instr[0] == 'CONST'


def _const_val(instr):
    return instr[1]


def _opcode(instr):
    return instr[0]


# Aritmética com casting consistente: se algum lado é float, o resultado é
# float; caso contrário inteiro. As primitivas Python já tratam isto bem.
def _eval_binop(op, a, b):
    try:
        if op == '+':
            return a + b
        if op == '-':
            return a - b
        if op == '*':
            return a * b
        if op == '/':
            if isinstance(a, float) or isinstance(b, float):
                return a / b
            # divisão inteira (truncamento para zero, à la Fortran)
            q = abs(a) // abs(b)
            return q if (a < 0) == (b < 0) else -q
    except ZeroDivisionError:
        return None
    return None


def _eval_relop(op, a, b):
    if op == '.EQ.': return 1 if a == b else 0
    if op == '.NE.': return 1 if a != b else 0
    if op == '.LT.': return 1 if a <  b else 0
    if op == '.LE.': return 1 if a <= b else 0
    if op == '.GT.': return 1 if a >  b else 0
    if op == '.GE.': return 1 if a >= b else 0
    return None


# ----------------------- Passes ---------------------------------------------

# Constant folding: combina CONST + CONST + (BINOP|RELOP|LOGOP) num único CONST.
# Também colapsa CONST seguido de NEG, NOT e I2F.
def constant_folding(code):
    out = []
    i = 0
    while i < len(code):
        instr = code[i]
        # CONST, CONST, BINOP
        if (i + 2 < len(code)
            and _is_const(instr)
            and _is_const(code[i+1])
            and _opcode(code[i+2]) == 'BINOP'):
            a = _const_val(instr)
            b = _const_val(code[i+1])
            _, op, t = code[i+2]
            v = _eval_binop(op, a, b)
            if v is not None:
                out.append(ir.CONST(v, t))
                i += 3
                continue
        # CONST, CONST, RELOP
        if (i + 2 < len(code)
            and _is_const(instr)
            and _is_const(code[i+1])
            and _opcode(code[i+2]) == 'RELOP'):
            a = _const_val(instr)
            b = _const_val(code[i+1])
            _, op, _t = code[i+2]
            v = _eval_relop(op, a, b)
            if v is not None:
                out.append(ir.CONST(v, 'logical'))
                i += 3
                continue
        # CONST, CONST, LOGOP
        if (i + 2 < len(code)
            and _is_const(instr)
            and _is_const(code[i+1])
            and _opcode(code[i+2]) == 'LOGOP'):
            a = _const_val(instr)
            b = _const_val(code[i+1])
            _, op = code[i+2]
            if op == 'and':
                v = 1 if (a and b) else 0
            else:
                v = 1 if (a or b) else 0
            out.append(ir.CONST(v, 'logical'))
            i += 3
            continue
        # CONST, NEG  →  CONST(-v)
        if (i + 1 < len(code)
            and _is_const(instr)
            and _opcode(code[i+1]) == 'NEG'):
            t = code[i+1][1]
            out.append(ir.CONST(-_const_val(instr), t))
            i += 2
            continue
        # CONST, NOT  →  CONST(!v)
        if (i + 1 < len(code)
            and _is_const(instr)
            and _opcode(code[i+1]) == 'NOT'):
            v = _const_val(instr)
            out.append(ir.CONST(0 if v else 1, 'logical'))
            i += 2
            continue
        # CONST(int), I2F  →  CONST(float)
        if (i + 1 < len(code)
            and _is_const(instr)
            and _opcode(code[i+1]) == 'I2F'):
            out.append(ir.CONST(float(_const_val(instr)), 'real'))
            i += 2
            continue
        out.append(instr)
        i += 1
    return out


# Identidades algébricas:
#   x op CONST_neutro  →  x   (com x sendo um único push de valor)
#   x op CONST_aniquilador  →  CONST_aniquilador  (se sem efeitos colaterais)
#
# Conservativo: só simplifica quando o operando esquerdo é um único push
# óbvio (CONST, LOAD, LOADL) — i.e., 1 instrução.
def algebraic_simplification(code):
    SINGLE_PUSH = {'CONST', 'LOAD', 'LOADL'}
    out = []
    i = 0
    while i < len(code):
        if (i + 2 < len(code)
            and _opcode(code[i]) in SINGLE_PUSH
            and _is_const(code[i+1])
            and _opcode(code[i+2]) == 'BINOP'):
            x = code[i]
            c = _const_val(code[i+1])
            _, op, t = code[i+2]
            # Identidade à direita: x + 0, x - 0, x * 1, x / 1
            if op in ('+', '-') and c == 0:
                out.append(x); i += 3; continue
            if op in ('*', '/') and c == 1:
                out.append(x); i += 3; continue
            # Aniquilador à direita: x * 0  →  0  (válido só se x não é
            # uma chamada com side-effects; CONST/LOAD/LOADL são puros).
            if op == '*' and c == 0:
                out.append(ir.CONST(0 if t == 'integer' else 0.0, t))
                i += 3; continue

        if (i + 2 < len(code)
            and _is_const(code[i])
            and _opcode(code[i+1]) in SINGLE_PUSH
            and _opcode(code[i+2]) == 'BINOP'):
            c = _const_val(code[i])
            x = code[i+1]
            _, op, t = code[i+2]
            # Identidade à esquerda: 0 + x, 1 * x
            if op == '+' and c == 0:
                out.append(x); i += 3; continue
            if op == '*' and c == 1:
                out.append(x); i += 3; continue
            # Aniquilador à esquerda: 0 * x  →  0
            if op == '*' and c == 0:
                out.append(ir.CONST(0 if t == 'integer' else 0.0, t))
                i += 3; continue

        out.append(code[i])
        i += 1
    return out


# Branch folding: JZ com condição CONST resolve-se em JUMP ou em nada.
def branch_folding(code):
    out = []
    i = 0
    while i < len(code):
        instr = code[i]
        if (i + 1 < len(code)
            and _is_const(instr)
            and _opcode(code[i+1]) == 'JZ'):
            v = _const_val(instr)
            label = code[i+1][1]
            if v == 0:
                out.append(ir.JUMP(label))   # condição falsa → salta
            # senão: condição verdadeira, queda natural
            i += 2
            continue
        out.append(instr)
        i += 1
    return out


# Remoção de código morto após instruções que terminam fluxo (JUMP, HALT,
# RETURN) — descarta tudo até à próxima LABEL.
def dead_code_elimination(code):
    TERMINATORS = {'JUMP', 'HALT', 'RETURN'}
    out = []
    i = 0
    skipping = False
    while i < len(code):
        instr = code[i]
        if skipping:
            if _opcode(instr) == 'LABEL':
                skipping = False
                out.append(instr)
            i += 1
            continue
        out.append(instr)
        if _opcode(instr) in TERMINATORS:
            skipping = True
        i += 1
    return out


# Jump threading e label coalescing:
#   JUMP L; L:           → L:                   (queda imediata)
#   L1: L2: ...          → L1:; substitui L2 por L1 em todo o lado
#   JUMP L1; ...; L1: JUMP L2 → JUMP L2; ...; L1: JUMP L2  (transitivo)
def jump_threading(code):
    # 1. Coalesce labels consecutivas: substitui todas as ocorrências de
    #    labels redundantes por um representante.
    aliases = {}
    i = 0
    while i < len(code) - 1:
        if _opcode(code[i]) == 'LABEL' and _opcode(code[i+1]) == 'LABEL':
            keep, drop = code[i][1], code[i+1][1]
            # Resolve cadeia de aliases: se 'keep' já foi substituído antes,
            # o representante final é o que está em aliases[keep].
            keep_root = aliases.get(keep, keep)
            aliases[drop] = keep_root
        i += 1

    def resolve(lbl):
        seen = set()
        while lbl in aliases and lbl not in seen:
            seen.add(lbl)
            lbl = aliases[lbl]
        return lbl

    new_code = []
    for instr in code:
        op = _opcode(instr)
        if op == 'LABEL' and instr[1] in aliases:
            continue                      # remove a label redundante
        if op == 'JUMP':
            new_code.append(ir.JUMP(resolve(instr[1])))
        elif op == 'JZ':
            new_code.append(ir.JZ(resolve(instr[1])))
        elif op == 'PUSHA':
            new_code.append(ir.PUSHA(resolve(instr[1])))
        else:
            new_code.append(instr)

    # 2. Remover JUMP imediatamente seguido pelo seu próprio alvo.
    out = []
    i = 0
    while i < len(new_code):
        instr = new_code[i]
        if (_opcode(instr) == 'JUMP'
            and i + 1 < len(new_code)
            and _opcode(new_code[i+1]) == 'LABEL'
            and new_code[i+1][1] == instr[1]):
            i += 1                        # fica só com a LABEL
            continue
        out.append(instr)
        i += 1

    # 3. Threading transitivo: JUMP A onde A: JUMP B  →  JUMP B.
    label_targets = {}
    for j, ins in enumerate(out):
        if _opcode(ins) == 'LABEL' and j + 1 < len(out) and _opcode(out[j+1]) == 'JUMP':
            label_targets[ins[1]] = out[j+1][1]

    def chase(lbl):
        seen = set()
        while lbl in label_targets and lbl not in seen:
            seen.add(lbl)
            lbl = label_targets[lbl]
        return lbl

    threaded = []
    for ins in out:
        op = _opcode(ins)
        if op == 'JUMP':
            threaded.append(ir.JUMP(chase(ins[1])))
        elif op == 'JZ':
            threaded.append(ir.JZ(chase(ins[1])))
        else:
            threaded.append(ins)
    return threaded


# Remove labels que nunca são referenciadas: nem por JUMP/JZ/PUSHA, nem
# correspondem a entry points de subprogramas (estes resolvem-se via PUSHA
# por nome — se nenhum PUSHA referenciar a label, é seguro remover).
def remove_unused_labels(code):
    used = set()
    for ins in code:
        op = _opcode(ins)
        if op in ('JUMP', 'JZ', 'PUSHA'):
            used.add(ins[1])
    return [ins for ins in code
            if not (_opcode(ins) == 'LABEL' and ins[1] not in used)]


DEFAULT_PASSES = [
    constant_folding,
    algebraic_simplification,
    branch_folding,
    dead_code_elimination,
    jump_threading,
    remove_unused_labels,
]
