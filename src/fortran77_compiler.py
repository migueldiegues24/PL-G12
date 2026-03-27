import sys
import os
from datetime import datetime

from syntax_analysis.lexer import lexer, find_column

def lexer_log(log_filepath, input_file, dt, codigo_fonte):
    try:
        with open(log_filepath, 'w', encoding='utf-8') as log_file:
            log_file.write(f"--- Relatório de Análise Léxica ---\n")
            log_file.write(f"Ficheiro Fonte: {input_file}\n")
            log_file.write(f"Data/Hora: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write("-" * 35 + "\n\n")
            
            count = 0
            for token in lexer:
                coluna = find_column(codigo_fonte, token)
                
                log_file.write(f"LexToken({token.type}, {repr(token.value)}, line={token.lineno}, col={coluna})\n")
                count += 1
            
            log_file.write(f"\nTotal de tokens processados: {count}\n")
            print(f"Log gerado com sucesso em: {log_filepath}")

    except Exception as e:
        print(f"Ocorreu um erro ao escrever no ficheiro de log: {e}")


def main():
    if len(sys.argv) < 2:
        print("Argumentos Insuficientes.")
        print("Exemplo: python3 fortran77_compiler.py examples/exemplo1_hello.f")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Erro: O ficheiro '{input_file}' não foi encontrado.")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        codigo_fonte = f.read()

    dt = datetime.now()
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"{timestamp}_lexer_output.log"
    
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_filepath = os.path.join(log_dir, log_filename)

    print(f"A executar análise léxica: {input_file}...")
    
    lexer.input(codigo_fonte)

    lexer_log(log_filepath, input_file, dt, codigo_fonte)


if __name__ == "__main__":
    main()