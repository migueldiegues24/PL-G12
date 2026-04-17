import sys
import os
from datetime import datetime
import pprint

# Imports do teu compilador
from syntax_analysis.lexer import lexer
from syntax_analysis.parser import parser

def save_log(filepath, content, title, input_file, dt):
    """Função genérica para salvar logs formatados"""
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
        print("\033[92mSucesso:\033[0m Programa gramaticalmente correto.")
    else:
        print("\033[91mErro:\033[0m A análise sintática falhou.")

if __name__ == "__main__":
    main()