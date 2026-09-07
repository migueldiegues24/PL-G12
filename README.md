# Fortran 77 → EWVM Compiler
 
A compiler for a subset of Fortran 77 (ANSI X3.9-1978), written from scratch in Python, targeting a stack-based virtual machine (EWVM). It implements the full standard compiler pipeline plus an optimization pass, and ships with 63 unit tests covering every stage.
 
```
source (.f) → lexer → parser → semantic analysis → IR builder → optimizer → emitter → EWVM assembly
```
 
Built for the Language Processing course at the University of Minho. Team of 3; my focus was the semantic analysis and code generation stages.
 
## Features
 
- **Lexer & parser** (`ply.lex` / `ply.yacc`) supporting `PROGRAM`, `FUNCTION`, `SUBROUTINE`, typed declarations (`INTEGER`, `REAL`, `LOGICAL`), 1D arrays, arithmetic/logical/relational expressions, `IF`/`IF-THEN-ELSE`, `DO` loops with labels, `GOTO`, `READ`/`PRINT`, and user-defined functions and subroutines.
- **Semantic analysis** with a two-pass symbol table (global subprogram registration, then scoped type-checking and annotation), 35+ built-in intrinsic functions, and Fortran-77-correct scoping rules (a function cannot see the caller's local variables).
- **Custom intermediate representation** — a flat list of postfix instructions — that decouples the language front-end from the target machine and enables independent optimization passes.
- **Optimizer**: constant folding, algebraic simplification, branch folding, dead code elimination, jump threading, and unused-label removal.
- **Code generator** that resolves Fortran's 1-based array indexing to the VM's 0-based model and picks integer vs. floating-point instruction variants based on inferred types.
- **63 unit tests** across lexer, parser, semantic analysis, and code generation (including per-pass optimizer smoke tests and full-pipeline tests).
## A couple of interesting problems solved
 
- **`F(I)` is ambiguous** — in Fortran 77 it can be a function call or an array access, and the grammar alone can't tell them apart. The parser emits a generic `call_or_array` node; semantic analysis resolves it using the symbol table, since only that stage knows whether `F` is a function or an array.
- **A silent runtime bug in the reference VM**: the EWVM documentation states that `RETURN` resets the stack pointer to free a subprogram's local variables, but the actual implementation doesn't. This caused callers to read stale stack values instead of the real return value. Diagnosed by stepping through the VM's operand stack in its debugger and watching it grow by 4 slots per call; fixed by emitting an explicit `POP` for the locals before every `RETURN`.
## Project structure
 
```
src/
├── fortran77_compiler.py     # entry point
├── syntax_analysis/          # lexer, parser, grammar rules
├── semantic_analysis/        # symbol table, type rules, built-ins
├── code_generation/          # IR, optimizer, emitter
├── examples/                 # sample Fortran 77 programs
└── tests/                    # 63 unit tests
```
 
## Running it
 
```bash
cd src
python3 -m venv venv
./venv/bin/pip install ply
 
./venv/bin/python fortran77_compiler.py examples/exemplo5_conversor.f
# generated .asm and stage logs land in logs/
 
./venv/bin/python -m unittest discover -s tests
```
 
The generated `.asm` file can be run directly in the [EWVM web interface](https://ewvm.epl.di.uminho.pt/).
 
## Known limitations
 
- Arguments are passed by value, not by reference (the EWVM target has no direct reference support).
- No local arrays inside functions/subroutines (only global arrays in the main program).
- `DO` loops assume a positive step.
- A handful of built-ins (`SIN`, `COS`, `LOG`, ...) are recognized by semantic analysis but not yet implemented in the code generator.
 
