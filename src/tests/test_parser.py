import unittest
import os

from syntax_analysis.lexer import lexer
from syntax_analysis.parser import parser


class TestFortranParserExamples(unittest.TestCase):

    def parse_file(self, filepath):
        self.assertTrue(os.path.exists(filepath), f"Ficheiro não encontrado: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            codigo = f.read()
        lexer.lineno = 1
        return parser.parse(codigo, lexer=lexer)

    def assert_is_program(self, ast):
        self.assertIsNotNone(ast, "Parser devolveu None — erro sintático.")
        self.assertEqual(ast[0], 'program')
        self.assertIsInstance(ast[1], list)
        self.assertGreater(len(ast[1]), 0)

    def test_exemplo1_hello(self):
        ast = self.parse_file("examples/exemplo1_hello.f")
        self.assert_is_program(ast)
        main = ast[1][0]
        self.assertEqual(main[0], 'main_program')
        self.assertEqual(main[1], 'HELLO')

    def test_exemplo2_fatorial(self):
        ast = self.parse_file("examples/exemplo2_fatorial.f")
        self.assert_is_program(ast)
        main = ast[1][0]
        self.assertEqual(main[1], 'FATORIAL')
        body_items = main[2][1]
        kinds = [it[0] for it in body_items]
        self.assertIn('decl', kinds)
        self.assertIn('do', kinds)
        self.assertIn('labeled', kinds)

    def test_exemplo3_primo(self):
        ast = self.parse_file("examples/exemplo3_primo.f")
        self.assert_is_program(ast)
        main = ast[1][0]
        self.assertEqual(main[1], 'PRIMO')
        body_items = main[2][1]
        kinds = [it[0] for it in body_items]
        self.assertIn('if_then_else', kinds)

    def test_exemplo4_soma(self):
        ast = self.parse_file("examples/exemplo4_soma.f")
        self.assert_is_program(ast)
        main = ast[1][0]
        self.assertEqual(main[1], 'SOMAARR')
        body_items = main[2][1]
        decl = next(it for it in body_items if it[0] == 'decl' and it[2][0][0] == 'array_decl')
        self.assertEqual(decl[2][0], ('array_decl', 'NUMS', 5))

    def test_exemplo5_conversor(self):
        ast = self.parse_file("examples/exemplo5_conversor.f")
        self.assert_is_program(ast)
        self.assertEqual(len(ast[1]), 2, "Esperava programa principal + função")
        self.assertEqual(ast[1][0][0], 'main_program')
        self.assertEqual(ast[1][1][0], 'function')
        self.assertEqual(ast[1][1][2], 'CONVRT')
        self.assertEqual(ast[1][1][3], ['N', 'B'])

    def test_erro_sintatico_sem_end(self):
        lexer.lineno = 1
        ast = parser.parse("PROGRAM X\n", lexer=lexer)
        self.assertIsNone(ast)


if __name__ == '__main__':
    unittest.main()
