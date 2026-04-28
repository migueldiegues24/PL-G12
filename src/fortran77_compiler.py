import sys
import os
from datetime import datetime
import pprint

from syntax_analysis.lexer import lexer
from syntax_analysis.parser import parser
from semantic_analysis.analyser import SemanticAnalyser
from code_generation.builder import IRBuilder
from code_generation.optimizer import optimize
from code_generation.emitter import Emitter

def save_log(filepath, content, title, input_file, dt):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"--- {title} ---\n")
            f.write(f"Ficheiro Fonte: {input_file}\n")
            f.write(f"Data/Hora: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 40 + "\n\n")
            
            if isinstance(content, (list, tuple)):
                f.write(pprint.pformat(content, indent=2, width=80))
            else:
                f.write(str(content))
                
            print(f"Log de {title} gerado em: {filepath}")
    except Exception as e:
        print(f"Erro ao gravar log: {e}")

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 fortran77_compiler.py examples/exemplo.f")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Erro: Ficheiro '{input_file}' não encontrado.")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        codigo_fonte = f.read()

    dt = datetime.now()
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 1. Análise léxica
    print(f"A executar análise léxica: {input_file}...")
    lexer.input(codigo_fonte)
    tokens_list = [str(tok) for tok in lexer]
    lexer_log_path = os.path.join(log_dir, f"{timestamp}_lexer.log")
    save_log(lexer_log_path, "\n".join(tokens_list), "Relatório Léxico", input_file, dt)

    # 2. ANÁLISE SINTÁTICA
    print(f"A executar análise sintática: {input_file}...")
    ast = parser.parse(codigo_fonte)

    if ast:
        parser_log_path = os.path.join(log_dir, f"{timestamp}_parser_ast.log")
        save_log(parser_log_path, ast, "Árvore Sintática Abstrata (AST)", input_file, dt)
        print("\033[92mSucesso:\033[0m Programa sintáticamente validade.")
    else:
        print("\033[91mErro:\033[0m A análise sintática falhou.")
        return

    # 3. ANÁLISE SEMÂNTICA
    print(f"A executar análise semântica: {input_file}...")
    analyser = SemanticAnalyser()
    annotated_ast, _, reporter = analyser.analyse(ast)

    semantic_log_path = os.path.join(log_dir, f"{timestamp}_semantic_ast.log")
    save_log(semantic_log_path, annotated_ast, "AST Anotada (Semântica)", input_file, dt)

    if reporter.has_errors():
        print(f"\033[91mErro:\033[0m Análise semântica falhou com {reporter.count()} erro(s).")
        return
    print("\033[92mSucesso:\033[0m Programa semânticamente válido.")

    # 4. GERAÇÃO DE CÓDIGO (IR → optimize → EWVM)
    print(f"A gerar IR: {input_file}...")
    builder = IRBuilder(analyser.table)
    ir_code, layout = builder.build(annotated_ast)

    ir_log_path = os.path.join(log_dir, f"{timestamp}_ir.log")
    save_log(ir_log_path, ir_code, "Representação Intermédia (IR)", input_file, dt)

    optimized = optimize(ir_code)
    if optimized is not ir_code:
        opt_log_path = os.path.join(log_dir, f"{timestamp}_ir_optimized.log")
        save_log(opt_log_path, optimized, "IR Otimizada", input_file, dt)

    print("A gerar código EWVM...")
    asm = Emitter(layout).emit(optimized)
    asm_log_path = os.path.join(log_dir, f"{timestamp}_ewvm.asm")
    save_log(asm_log_path, "\n".join(asm), "Código EWVM", input_file, dt)
    print("\033[92mSucesso:\033[0m Código EWVM gerado.")


if __name__ == "__main__":
    main()