# Compilador para Fortran 77 → EWVM

**Processamento de Linguagens · LEI · 2025/2026 · Grupo 12**

| Número  | Nome                              |
|---------|-----------------------------------|
| A104004 | Diogo José Fernandes Esteves      |
| A104433 | Francisco Jorge Salgado Castro    |
| A107361 | Miguel Rocha Diegues              |


---

## 1. Objetivo e visão geral

O trabalho implementa um compilador para um subconjunto do Fortran 77 standard (ANSI X3.9-1978) que produz assembly da máquina virtual EWVM. O pipeline cobre as quatro fases obrigatórias e a fase de valorização (otimização):

```
fonte .f  →  lexer  →  parser  →  analisador semântico
          →  IR builder  →  optimizer  →  emitter  →  .asm EWVM
```

Cada fase está num módulo independente em `src/`, comunica por estruturas Python explícitas (lista de tokens, AST anotada, lista de instruções IR, lista de strings) e produz um log em `src/logs/` para inspeção. O ponto de entrada é `src/fortran77_compiler.py`.

São suportados todos os exemplos do enunciado: programa principal, declarações de tipo (`INTEGER`, `REAL`, `LOGICAL`), arrays unidimensionais, expressões aritméticas / lógicas / relacionais, `IF` / `IF-THEN-ELSE`, `DO` com label e `CONTINUE`, `GOTO`, `READ` / `PRINT`, e ainda `FUNCTION` / `SUBROUTINE` definidas pelo utilizador (valorização).

---

## 2. Análise léxica

Implementada com `ply.lex` em [src/syntax_analysis/lexer.py](src/syntax_analysis/lexer.py). Optámos pelo **formato livre** (em vez do formato de colunas fixas), uma vez que torna a escrita dos exemplos mais natural e simplifica a expressão regular do lexer — o utilizador pode endentar livremente.

Pontos relevantes:
- Os operadores relacionais e lógicos do Fortran 77 são *bracketed* por pontos (`.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.`, `.AND.`, `.OR.`, `.NOT.`) e foram reconhecidos diretamente como tokens próprios.
- Literais lógicos `.TRUE.` / `.FALSE.` produzem um token `BOOL` com o valor Python `True` / `False`, simplificando a propagação de tipos no parser.
- Identificadores e palavras-chave partilham a mesma expressão regular: o `t_IDENTIFIER` consulta um dicionário `keywords` para promover o token ao tipo apropriado (`PROGRAM`, `INTEGER`, `IF`, ...). Isto evita ter uma regra separada por cada palavra-chave.
- `NEWLINE` é um token explícito, porque em Fortran 77 a quebra de linha tem significado sintático (separa statements).
- Strings (`STRING`) são lidas com `'[^']*'` e o valor armazenado já vem sem aspas para reuso direto no `PUSHS`.

Os erros léxicos são relatados com linha + coluna; o lexer continua para reportar todos os erros do ficheiro num único *run*.

---

## 3. Análise sintática

Implementada com `ply.yacc` em [src/syntax_analysis/parser.py](src/syntax_analysis/parser.py); as regras estão divididas por temas em [src/syntax_analysis/rules/](src/syntax_analysis/rules/) (programa, declarações, statements, expressões), com o objetivo de manter cada ficheiro pequeno.

A gramática (ver os ficheiros `rules_*.py` para a versão exata):

```
Programa       : Unidade+
Unidade        : ProgramaPrincipal | Subprograma
ProgramaPrincipal : 'PROGRAM' ID newlines Corpo 'END'
Subprograma    : (Tipo)? 'FUNCTION' ID '(' ListaParams ')' newlines Corpo 'END'
               | 'SUBROUTINE' ID ('(' ListaParams ')')? newlines Corpo 'END'
Corpo          : (Declaracao | Statement)*
Declaracao     : Tipo VarDecl (',' VarDecl)* newlines
VarDecl        : ID | ID '(' NUMBER ')'        -- escalar ou array

Statement      : (NUMBER)? StmtSimples         -- label opcional
StmtSimples    : Atribuicao | If | IfBloco | Do | Goto | Return
               | Continue | Read | Print | Call

Expr           : Expr '.OR.' TermoLog | TermoLog
TermoLog       : TermoLog '.AND.' FatorLog | FatorLog
FatorLog       : '.NOT.' FatorLog | ExprRel
ExprRel        : ExprArit OpRel ExprArit | ExprArit
ExprArit       : ExprArit ('+' | '-') Termo  | Termo
Termo          : Termo ('*' | '/') Fator      | Fator
Fator          : ('-' | '+') Fator
               | NUMBER | BOOL | STRING | ID
               | ID '(' ListaExprs ')'        -- chamada OU acesso a array
               | '(' Expr ')'
```

Resolvemos a precedência de operadores via `precedence` no `ply.yacc` (`OR < AND < NOT < relacionais < + - < * /`), o que reduziu drasticamente a hierarquia de não-terminais necessária. Mantivemos ainda assim alguns níveis explícitos (`expressao`, `termo_logico`, `fator_logico`, ...) para forçar associatividades.

**Ambiguidade `ID(args)`**: em Fortran 77, `F(I)` pode ser uma chamada a função ou um acesso a array — o parser não consegue distinguir só com a gramática. Resolvemos como se segue: o parser produz um nó genérico `('call_or_array', NOME, args)` e a análise semântica (que tem acesso à tabela de símbolos) reescreve-o em `('call', ...)` ou `('index', ...)`.

A AST é uma árvore de tuplos imutáveis (em vez de classes), formato leve e fácil de inspecionar nos logs.

---

## 4. Análise semântica

Implementada em [src/semantic_analysis/analyser.py](src/semantic_analysis/analyser.py), com tabela de símbolos em [symbol_table.py](src/semantic_analysis/symbol_table.py), regras de tipos em [type_rules.py](src/semantic_analysis/type_rules.py) e funções intrínsecas em [builtins.py](src/semantic_analysis/builtins.py).

### 4.1 Estratégia em duas passagens

1. **Recolha de subprogramas**: percorre as unidades de topo e regista nomes de `FUNCTION` / `SUBROUTINE` no scope global. Necessária para validar chamadas a funções definidas DEPOIS do `PROGRAM` (caso do `exemplo5_conversor.f`).
2. **Visita da AST com anotação**: para cada expressão, calcula e propaga o tipo num dicionário `{'type': ...}` no último elemento do tuplo (ex: `('binop', '+', l, r, {'type': 'integer'})`). Também valida declarações duplicadas, atribuições incompatíveis, índices não-inteiros, condições não-lógicas, parâmetros em número errado, labels não definidas, etc.

### 4.2 Tabela de símbolos

A `SymbolTable` mantém uma pilha de scopes mas com uma regra de visibilidade restrita: o lookup só consulta o scope corrente e o scope global — uma função NÃO vê as variáveis do `PROGRAM`, conforme o standard Fortran 77. Cada scope tem ainda um *namespace* separado para labels (`10`, `20`, ...).

Nuances tratadas:
- O nome da função vive simultaneamente no scope global (como símbolo `function`) e no scope local (como variável do tipo de retorno) — em Fortran 77 atribuir ao próprio nome da função define o valor de retorno (ex: `CONVRT = VAL`).
- A declaração `INTEGER CONVRT` no `PROGRAM` é uma *forward declaration* do tipo de retorno de uma função externa; é detetada e fundida com o símbolo global em vez de criar uma variável local.
- Os parâmetros são declarados como `kind='param'`. A regra de inicialização aceita `'var'` e `'param'` porque os parâmetros são modificáveis dentro do subprograma.

### 4.3 Built-ins

Registamos 35+ funções intrínsecas (`MOD`, `ABS`, `SQRT`, conversões, trigonometria, ...) com a sua assinatura. Isto torna a verificação de chamadas uniforme e permite que o gerador de código reconheça quais expandir como instrução EWVM nativa (ex: `MOD` → `MOD`).

---

## 5. Tradução para a EWVM

A geração de código está separada em três passos para isolar responsabilidades:

```
AST anotada  →  IR Builder  →  Optimizer  →  Emitter  →  assembly EWVM
```

### 5.1 Representação intermédia (IR)

A IR ([src/code_generation/ir.py](src/code_generation/ir.py)) é uma **lista linear de instruções postfix**, próxima do nível EWVM mas ainda com *labels* e *nomes simbólicos* por resolver. Cada instrução é um tuplo `(opcode, ...args)`. Operadores típicos: `CONST`, `LOAD`/`STORE` (globais), `LOADL`/`STOREL` (locais, com offset relativo a `fp`), `BINOP`, `RELOP`, `LOGOP`, `JUMP`, `JZ`, `LABEL`, `READ`, `WRITE`, `PUSHA`, `CALL_USER`, `RETURN`, `PUSHN`, `POPN`, `HALT`.

Esta camada existe por dois motivos: permite **otimizações independentes** da gramática (vê secção 5.4), e isola o emitter do builder, simplificando alterações futuras à máquina alvo.

### 5.2 Layout de memória

Dois layouts coexistem ([src/code_generation/layout.py](src/code_generation/layout.py)):

- **`GlobalLayout`** — atribui um offset (na zona global da pilha de operandos da EWVM, acedida via `gp`) a cada variável/array do `PROGRAM`. Variáveis simples ocupam 1 *slot*, arrays ocupam `size` *slots* contíguos.
- **`LocalLayout`** — atribui offsets relativos a `fp` para os parâmetros, slot de retorno e locais de uma função / subrotina (vê secção 5.3).

### 5.3 Convenção de chamada

Esta foi a parte mais delicada do projeto. Para cada `FUNCTION F(p1, ..., pN)`:

1. **No caller** (antes da chamada):
   - Empilha um *placeholder* (`PUSHI 0`) que servirá de slot de retorno.
   - Empilha os argumentos `arg1, ..., argN` pela ordem.
   - `PUSHA F` empilha o endereço da label.
   - `CALL` retira a label, guarda `pc`/`fp`, atribui `pc = endereço` e `fp = sp` (valor atual de `sp`).
2. **Layout dentro da função** (relativo a `fp`):
   - Slot de retorno (nome da função) em `fp[-(N+1)]`.
   - `argi` (1-based) em `fp[-(N - i + 1)]`.
   - Locais regulares em `fp[0]`, `fp[1]`, ...
3. **Preâmbulo da função**: `PUSHN k` aloca os *k* locais a zero.
4. **Saída da função**: atribuir ao nome da função (`CONVRT = VAL`) traduz-se em `STOREL` para o slot de retorno em `fp[-(N+1)]`. Antes de `RETURN`, descartamos explicitamente o frame local com `POP k` (ver secção 7).
5. **Após `CALL` no caller**: `POP N` descarta os argumentos. O slot de retorno fica no topo da pilha pronto para ser consumido (e.g., `STOREG` para uma variável).

Para `SUBROUTINE` é semelhante, mas sem slot de retorno: o caller não empilha *placeholder* nem tira valor depois.

### 5.4 Otimizações

Implementadas em [src/code_generation/optimizer.py](src/code_generation/optimizer.py) e ligadas por defeito. Cada *pass* recebe e devolve uma lista de instruções IR; o pipeline corre em **ponto-fixo** (até nada mudar) para apanhar transformações em cascata.

| Pass                       | Padrão                                              | Resultado                          |
|----------------------------|-----------------------------------------------------|------------------------------------|
| `constant_folding`         | `CONST a; CONST b; BINOP/RELOP/LOGOP`               | `CONST (a op b)`                   |
|                            | `CONST a; NEG/NOT/I2F`                              | `CONST (op a)`                     |
| `algebraic_simplification` | `x ± 0`, `x * 1`, `x / 1`                           | `x`                                |
|                            | `x * 0`                                             | `CONST 0`                          |
| `branch_folding`           | `CONST v; JZ L`                                     | `JUMP L` (se `v=0`) ou nada        |
| `dead_code_elimination`    | Código entre `JUMP/HALT/RETURN` e o próximo `LABEL` | Removido                           |
| `jump_threading`           | `LABEL A; LABEL B`                                  | Coalesce (substitui `B` por `A`)   |
|                            | `JUMP L; L:`                                        | Remove o `JUMP`                    |
|                            | `LABEL A; JUMP B` ⇒ qualquer `JUMP A`               | `JUMP B` (transitivo)              |
| `remove_unused_labels`     | `LABEL X` sem qualquer `JUMP/JZ/PUSHA X`            | Remove a label                     |

Conservadorismo deliberado: `algebraic_simplification` só age quando o operando "outro lado" é um *single push* puro (`CONST`, `LOAD`, `LOADL`), para não eliminar uma chamada ou uma sequência com efeitos colaterais.

### 5.5 Emitter

[src/code_generation/emitter.py](src/code_generation/emitter.py) traduz a IR em assembly EWVM linha a linha. A maior parte das instruções é mapeamento direto; merecem nota:

- `BINOP` / `RELOP` escolhem variantes inteiras ou flutuantes (`ADD` vs `FADD`, `INF` vs `FINF`, etc.) com base no tipo dos operandos.
- `.NE.` é traduzido como `EQUAL` + `NOT`, já que a EWVM não tem um operador "não igual" direto.
- `LOADIDX`/`STOREIDX` para arrays expandem para a sequência `PUSHGP; PUSHI offset; PADD; SWAP; PADD; LOAD 0` (e equivalente para escrita), com ajuste do índice 1-based de Fortran para 0-based da EWVM.
- `CALL_BUILTIN` consulta uma tabela `(nome, tipo_retorno) → instrução(ões) EWVM`. Inclui hoje `MOD`, `ABS`/`IABS`, `SQRT`, `REAL`/`FLOAT`, `INT`/`IFIX`. As restantes built-ins do `BUILTINS` ficam reconhecidas pela análise semântica mas falham no emitter (extensão futura).

---

## 6. Como correr

```bash
# 1. Criar venv e instalar dependências
cd src
python3 -m venv venv
./venv/bin/pip install ply

# 2. Compilar um exemplo
./venv/bin/python fortran77_compiler.py examples/exemplo5_conversor.f

# 3. Os logs aparecem em logs/<timestamp>_*.log e .asm
ls -t logs/

# 4. Correr os testes
./venv/bin/python -m unittest discover -s tests
```

O ficheiro `.asm` mais recente em `src/logs/` pode ser carregado diretamente em <https://ewvm.epl.di.uminho.pt/> ("Run" / "Load file"). Para os exemplos com `READ` o utilizador escreve o input no campo apropriado da interface.

Os logs gerados por compilação são:
- `<ts>_lexer.log` — sequência de tokens
- `<ts>_parser_ast.log` — AST sem anotações
- `<ts>_semantic_ast.log` — AST anotada com tipos
- `<ts>_ir.log` — IR antes da otimização
- `<ts>_ir_optimized.log` — IR depois da otimização (só se houver alterações)
- `<ts>_ewvm.asm` — código final EWVM

---

## 7. Dificuldades encontradas

**Ambiguidade chamada-vs-array.** Resolvido como descrito na secção 3 (nó intermédio `call_or_array` resolvido pela semântica).

**Dois conceitos de "nome da função".** O nome de uma `FUNCTION` aparece (1) globalmente como símbolo da função, (2) no `PROGRAM` como *forward declaration* do tipo de retorno (`INTEGER CONVRT`), e (3) localmente dentro da função como variável de retorno. Tivemos de garantir que cada uso é tratado no contexto certo, sem reservar slot global indevido nem rejeitar o uso de `CONVRT = VAL` dentro da própria função.

**Parâmetros como variáveis modificáveis.** Inicialmente o `SymbolTable.initialize` rejeitava qualquer `kind` diferente de `'var'`, o que falhava em `T = X` quando `X` era um parâmetro. Corrigido para aceitar também `kind='param'`.

**Comportamento de `RETURN` na EWVM web.** A documentação afirma que `RETURN` faz `sp = fp` (devolvendo o espaço dos locais alocados por `PUSHN`), mas a implementação observada em `ewvm.epl.di.uminho.pt` não cumpre isso: os locais ficavam na pilha. O sintoma era que, em vez de o caller ler o valor de retorno via `STOREG`, ele lia o `REM` da última iteração. Solução: emitir explicitamente `POP k` antes de cada `RETURN` em subprogramas com `k` locais. Esta foi de longe a *bug story* mais demorada — só foi diagnosticada depois de inspecionar o estado da pilha de operandos no debugger da EWVM e ver que o `sp` crescia 4 *slots* por chamada.

**Ciclos `DO ... <label> CONTINUE`.** Em Fortran 77 o corpo do `DO` termina implicitamente no statement com a label do `DO`. Modelámos isto com uma pilha interna no IR builder: o `_stmt_do` empilha `(label_alvo, var, step, L_top, L_end)`, e cada `_stmt_labeled` verifica se a sua label fecha o `DO` no topo, emitindo nesse caso a instrução de incremento, o `JUMP` para o topo e a `LABEL` final.

**Prevenir conflitos de tabelas geradas pelo PLY entre execuções.** Optámos por criar o parser com `yacc(write_tables=False)`, evitando que o PLY escreva ficheiros `parser.out` / `parsetab.py` no projeto.

---

## 8. Limitações conhecidas

- **Passagem de argumentos por valor.** O standard Fortran 77 especifica passagem por referência, mas a EWVM não tem suporte direto a referências. A nossa convenção passa por valor: os subprogramas podem ler e modificar localmente os parâmetros, mas as alterações não são visíveis no caller. Os exemplos do enunciado não dependem desta semântica (o `exemplo5_conversor.f` retorna via nome da função).
- **Sem arrays locais em subprogramas.** Suportamos arrays globais (no `PROGRAM`); arrays declarados dentro de uma `FUNCTION`/`SUBROUTINE` não estão implementados (não foram exigidos por nenhum exemplo).
- **`DO` apenas com passo positivo** assumido no corpo do compilador (a comparação no topo do ciclo é `var .LE. limite`). Negativos exigiriam emitir condicionalmente `.GE.` em função do sinal do step.
- **Algumas built-ins reconhecidas mas não emitidas.** `SIN`, `COS`, `LOG`, etc., são aceites pela análise semântica mas o `Emitter` ainda não as expande (lança `NotImplementedError`).

---

## 9. Estrutura do repositório

```
src/
├── fortran77_compiler.py        # ponto de entrada
├── syntax_analysis/
│   ├── lexer.py
│   ├── parser.py
│   └── rules/                   # regras YACC por tema
├── semantic_analysis/
│   ├── analyser.py
│   ├── symbol_table.py
│   ├── type_rules.py
│   ├── builtins.py
│   └── semantic_errors.py
├── code_generation/
│   ├── ir.py                    # construtores de instruções IR
│   ├── layout.py                # GlobalLayout, LocalLayout
│   ├── builder.py               # AST anotada → IR
│   ├── optimizer.py             # passes de otimização
│   └── emitter.py               # IR → assembly EWVM
├── examples/                    # 5 do enunciado + 2 nossos
└── tests/                       # 63 testes unitários
```

---

## 10. Testes

Foram escritos 63 testes unitários, distribuídos por:

- `test_lexer.py` — 7 testes (tokens, palavras-chave, números, strings, BOOL).
- `test_parser.py` — 14 testes (programa, declarações, statements, expressões, recuperação de erros).
- `test_semantic.py` — 21 testes (5 exemplos do enunciado + 16 casos de erro: tipos incompatíveis, variáveis não declaradas, índices errados, labels duplicadas, etc.).
- `test_codegen.py` — 21 testes (assembly bem-formado para os 6 exemplos, *smoke-test* de cada *pass* do optimizador isoladamente, pipeline completo com optimizador ligado).

Correr: `./venv/bin/python -m unittest discover -s tests` na pasta `src/`.

---

## 11. Conclusão

Este projeto cobre integralmente as quatro fases obrigatórias do enunciado e a fase de valorização (otimização + subprogramas). A separação em IR + optimizer + emitter permitiu acrescentar funções e subrotinas sem tocar nas fases anteriores e isolar a única correção *runtime* específica da EWVM (o `POP k` antes do `RETURN`) num único sítio. Os 63 testes unitários servem de regression suite para futuras alterações.
