import unittest
import os

from syntax_analysis.lexer import lexer

class TestFortranLexerExamples(unittest.TestCase):
    
    def get_tokens_from_file(self, filepath):
        self.assertTrue(os.path.exists(filepath), f"Ficheiro não encontrado: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            codigo = f.read()
            
        lexer.input(codigo)
        return [tok for tok in lexer]

    def assert_token_sequence(self, tokens, expected):
        """
        Testa uma sequência de tokens.
        'expected' é uma lista de tuplos: (TIPO,) ou (TIPO, VALOR).
        """
        for i, exp in enumerate(expected):
            tok = tokens[i]
            self.assertEqual(tok.type, exp[0], f"Erro no índice {i}: Esperava TIPO '{exp[0]}', recebi '{tok.type}' (Valor: {tok.value})")
            
            if len(exp) > 1:
                self.assertEqual(tok.value, exp[1], f"Erro no índice {i}: Esperava VALOR '{exp[1]}', recebi '{tok.value}'")

    def test_exemplo1_hello_mundo(self):
        tokens = self.get_tokens_from_file("examples/exemplo1_hello.f")
        
        expected = [
            ('PROGRAM',), ('IDENTIFIER', 'HELLO'), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'Ola, Mundo!'), ('NEWLINE',),
            ('END',)
        ]
        self.assert_token_sequence(tokens, expected)


    def test_exemplo2_fatorial(self):
        tokens = self.get_tokens_from_file("examples/exemplo2_fatorial.f")
        
        expected = [
            ('PROGRAM',), ('IDENTIFIER', 'FATORIAL'), ('NEWLINE',),
            ('INTEGER',), ('IDENTIFIER', 'N'), ('COMMA',), ('IDENTIFIER', 'I'), ('COMMA',), ('IDENTIFIER', 'FAT'), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'Introduza um numero inteiro positivo:'), ('NEWLINE',),
            ('READ',), ('TIMES',), ('COMMA',), ('IDENTIFIER', 'N'), ('NEWLINE',),
            ('IDENTIFIER', 'FAT'), ('ASSIGN',), ('NUMBER', 1), ('NEWLINE',),
            ('DO',), ('NUMBER', 10), ('IDENTIFIER', 'I'), ('ASSIGN',), ('NUMBER', 1), ('COMMA',), ('IDENTIFIER', 'N'), ('NEWLINE',),
            ('IDENTIFIER', 'FAT'), ('ASSIGN',), ('IDENTIFIER', 'FAT'), ('TIMES',), ('IDENTIFIER', 'I'), ('NEWLINE',),
            ('NUMBER', 10), ('CONTINUE',), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'Fatorial de'), ('COMMA',), ('IDENTIFIER', 'N'), ('COMMA',), ('STRING', ':'), ('COMMA',), ('IDENTIFIER', 'FAT'), ('NEWLINE',),
            ('END',)
        ]
        self.assert_token_sequence(tokens, expected)


    def test_exemplo3_primo(self):
        tokens = self.get_tokens_from_file("examples/exemplo3_primo.f")
        
        expected = [
            ('PROGRAM',), ('IDENTIFIER', 'PRIMO'), ('NEWLINE',),
            ('INTEGER',), ('IDENTIFIER', 'NUM'), ('COMMA',), ('IDENTIFIER', 'I'), ('NEWLINE',),
            ('LOGICAL',), ('IDENTIFIER', 'ISPRIM'), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'Introduza um numero inteiro positivo:'), ('NEWLINE',),
            ('READ',), ('TIMES',), ('COMMA',), ('IDENTIFIER', 'NUM'), ('NEWLINE',),
            ('IDENTIFIER', 'ISPRIM'), ('ASSIGN',), ('BOOL', True), ('NEWLINE',),
            ('IDENTIFIER', 'I'), ('ASSIGN',), ('NUMBER', 2), ('NEWLINE',),
            ('NUMBER', 20), ('IF',), ('LPAREN',), ('IDENTIFIER', 'I'), ('LE',), ('LPAREN',), ('IDENTIFIER', 'NUM'), ('DIVIDE',), ('NUMBER', 2), ('RPAREN',), ('AND',), ('IDENTIFIER', 'ISPRIM'), ('RPAREN',), ('THEN',), ('NEWLINE',),
            ('IF',), ('LPAREN',), ('IDENTIFIER', 'MOD'), ('LPAREN',), ('IDENTIFIER', 'NUM'), ('COMMA',), ('IDENTIFIER', 'I'), ('RPAREN',), ('EQ',), ('NUMBER', 0), ('RPAREN',), ('THEN',), ('NEWLINE',),
            ('IDENTIFIER', 'ISPRIM'), ('ASSIGN',), ('BOOL', False), ('NEWLINE',),
            ('ENDIF',), ('NEWLINE',),
            ('IDENTIFIER', 'I'), ('ASSIGN',), ('IDENTIFIER', 'I'), ('PLUS',), ('NUMBER', 1), ('NEWLINE',),
            ('GOTO',), ('NUMBER', 20), ('NEWLINE',),
            ('ENDIF',), ('NEWLINE',),
            ('IF',), ('LPAREN',), ('IDENTIFIER', 'ISPRIM'), ('RPAREN',), ('THEN',), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('IDENTIFIER', 'NUM'), ('COMMA',), ('STRING', ' e um numero primo'), ('NEWLINE',),
            ('ELSE',), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('IDENTIFIER', 'NUM'), ('COMMA',), ('STRING', ' nao e um numero primo'), ('NEWLINE',),
            ('ENDIF',), ('NEWLINE',),
            ('END',)
        ]
        self.assert_token_sequence(tokens, expected)


    def test_exemplo4_soma_lista(self):
        tokens = self.get_tokens_from_file("examples/exemplo4_soma.f")
        
        expected = [
            ('PROGRAM',), ('IDENTIFIER', 'SOMAARR'), ('NEWLINE',),
            ('INTEGER',), ('IDENTIFIER', 'NUMS'), ('LPAREN',), ('NUMBER', 5), ('RPAREN',), ('NEWLINE',),
            ('INTEGER',), ('IDENTIFIER', 'I'), ('COMMA',), ('IDENTIFIER', 'SOMA'), ('NEWLINE',),
            ('IDENTIFIER', 'SOMA'), ('ASSIGN',), ('NUMBER', 0), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'Introduza 5 numeros inteiros:'), ('NEWLINE',),
            ('DO',), ('NUMBER', 30), ('IDENTIFIER', 'I'), ('ASSIGN',), ('NUMBER', 1), ('COMMA',), ('NUMBER', 5), ('NEWLINE',),
            ('READ',), ('TIMES',), ('COMMA',), ('IDENTIFIER', 'NUMS'), ('LPAREN',), ('IDENTIFIER', 'I'), ('RPAREN',), ('NEWLINE',),
            ('IDENTIFIER', 'SOMA'), ('ASSIGN',), ('IDENTIFIER', 'SOMA'), ('PLUS',), ('IDENTIFIER', 'NUMS'), ('LPAREN',), ('IDENTIFIER', 'I'), ('RPAREN',), ('NEWLINE',),
            ('NUMBER', 30), ('CONTINUE',), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'A soma dos numeros e: '), ('COMMA',), ('IDENTIFIER', 'SOMA'), ('NEWLINE',),
            ('END',)
        ]
        self.assert_token_sequence(tokens, expected)


    def test_exemplo5_conversor_bases(self):
        tokens = self.get_tokens_from_file("examples/exemplo5_conversor.f")
        
        expected = [
            ('PROGRAM',), ('IDENTIFIER', 'CONVERSOR'), ('NEWLINE',),
            ('INTEGER',), ('IDENTIFIER', 'NUM'), ('COMMA',), ('IDENTIFIER', 'BASE'), ('COMMA',), ('IDENTIFIER', 'RESULT'), ('COMMA',), ('IDENTIFIER', 'CONVRT'), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'INTRODUZA UM NUMERO DECIMAL INTEIRO:'), ('NEWLINE',),
            ('READ',), ('TIMES',), ('COMMA',), ('IDENTIFIER', 'NUM'), ('NEWLINE',),
            ('DO',), ('NUMBER', 10), ('IDENTIFIER', 'BASE'), ('ASSIGN',), ('NUMBER', 2), ('COMMA',), ('NUMBER', 9), ('NEWLINE',),
            ('IDENTIFIER', 'RESULT'), ('ASSIGN',), ('IDENTIFIER', 'CONVRT'), ('LPAREN',), ('IDENTIFIER', 'NUM'), ('COMMA',), ('IDENTIFIER', 'BASE'), ('RPAREN',), ('NEWLINE',),
            ('PRINT',), ('TIMES',), ('COMMA',), ('STRING', 'BASE'), ('COMMA',), ('IDENTIFIER', 'BASE'), ('COMMA',), ('STRING', ':'), ('COMMA',), ('IDENTIFIER', 'RESULT'), ('NEWLINE',),
            ('NUMBER', 10), ('CONTINUE',), ('NEWLINE',),
            ('END',), ('NEWLINE',),
            ('INTEGER',), ('FUNCTION',), ('IDENTIFIER', 'CONVRT'), ('LPAREN',), ('IDENTIFIER', 'N'), ('COMMA',), ('IDENTIFIER', 'B'), ('RPAREN',), ('NEWLINE',),
            ('INTEGER',), ('IDENTIFIER', 'N'), ('COMMA',), ('IDENTIFIER', 'B'), ('COMMA',), ('IDENTIFIER', 'QUOT'), ('COMMA',), ('IDENTIFIER', 'REM'), ('COMMA',), ('IDENTIFIER', 'POT'), ('COMMA',), ('IDENTIFIER', 'VAL'), ('NEWLINE',),
            ('IDENTIFIER', 'VAL'), ('ASSIGN',), ('NUMBER', 0), ('NEWLINE',),
            ('IDENTIFIER', 'POT'), ('ASSIGN',), ('NUMBER', 1), ('NEWLINE',),
            ('IDENTIFIER', 'QUOT'), ('ASSIGN',), ('IDENTIFIER', 'N'), ('NEWLINE',),
            ('NUMBER', 20), ('IF',), ('LPAREN',), ('IDENTIFIER', 'QUOT'), ('GT',), ('NUMBER', 0), ('RPAREN',), ('THEN',), ('NEWLINE',),
            ('IDENTIFIER', 'REM'), ('ASSIGN',), ('IDENTIFIER', 'MOD'), ('LPAREN',), ('IDENTIFIER', 'QUOT'), ('COMMA',), ('IDENTIFIER', 'B'), ('RPAREN',), ('NEWLINE',),
            ('IDENTIFIER', 'VAL'), ('ASSIGN',), ('IDENTIFIER', 'VAL'), ('PLUS',), ('LPAREN',), ('IDENTIFIER', 'REM'), ('TIMES',), ('IDENTIFIER', 'POT'), ('RPAREN',), ('NEWLINE',),
            ('IDENTIFIER', 'QUOT'), ('ASSIGN',), ('IDENTIFIER', 'QUOT'), ('DIVIDE',), ('IDENTIFIER', 'B'), ('NEWLINE',),
            ('IDENTIFIER', 'POT'), ('ASSIGN',), ('IDENTIFIER', 'POT'), ('TIMES',), ('NUMBER', 10), ('NEWLINE',),
            ('GOTO',), ('NUMBER', 20), ('NEWLINE',),
            ('ENDIF',), ('NEWLINE',),
            ('IDENTIFIER', 'CONVRT'), ('ASSIGN',), ('IDENTIFIER', 'VAL'), ('NEWLINE',),
            ('RETURN',), ('NEWLINE',),
            ('END',)
        ]
        self.assert_token_sequence(tokens, expected)


if __name__ == '__main__':
    unittest.main()