import os
import unittest

from syntax_analysis.lexer import lexer
from syntax_analysis.parser import parser
from semantic_analysis.analyser import SemanticAnalyser
from code_generation.builder import IRBuilder
from code_generation.emitter import Emitter
from code_generation.optimizer import (
    optimize,
    constant_folding,
    algebraic_simplification,
    branch_folding,
    dead_code_elimination,
    jump_threading,
    remove_unused_labels,
)
from code_generation import ir


# Compila um ficheiro pelo pipeline completo e devolve o assembly EWVM (lista
# de strings). Falha o teste se houver erros léxicos/sintáticos/semânticos.
def compile_file(testcase, filepath, optimizer_passes=None):
    testcase.assertTrue(os.path.exists(filepath), f"Ficheiro não encontrado: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        codigo = f.read()

    lexer.lineno = 1
    ast = parser.parse(codigo, lexer=lexer)
    testcase.assertIsNotNone(ast, "Parser devolveu None — erro sintático.")

    analyser = SemanticAnalyser()
    annotated, table, reporter = analyser.analyse(ast)
    testcase.assertEqual(reporter.count(), 0,
                         f"Erros semânticos inesperados: {[e.message for e in reporter.errors]}")

    builder = IRBuilder(table)
    code, layout = builder.build(annotated)
    if optimizer_passes is not None:
        code = optimize(code, passes=optimizer_passes)
    return Emitter(layout).emit(code), code


# Pipeline completo, sem otimizações: cada exemplo deve gerar EWVM bem formado
# (start ... stop) e conter as instruções típicas do programa.
class TestCodeGenExamples(unittest.TestCase):

    def assert_basic_shape(self, asm):
        self.assertEqual(asm[0], 'start', "Programa deve começar com 'start'")
        self.assertIn('stop', asm, "Programa deve conter 'stop'")

    def test_exemplo1_hello(self):
        asm, _ = compile_file(self, "examples/exemplo1_hello.f")
        self.assert_basic_shape(asm)
        self.assertIn('PUSHS "Ola, Mundo!"', asm)
        self.assertIn('WRITES', asm)

    def test_exemplo2_fatorial(self):
        asm, _ = compile_file(self, "examples/exemplo2_fatorial.f")
        self.assert_basic_shape(asm)
        # Ciclo DO presente (label de início, JZ para fora, JUMP para topo).
        self.assertTrue(any(line.startswith('JZ ') for line in asm))
        self.assertTrue(any(line.startswith('JUMP ') for line in asm))

    def test_exemplo3_primo(self):
        asm, _ = compile_file(self, "examples/exemplo3_primo.f")
        self.assert_basic_shape(asm)
        # MOD intrínseca usada na verificação de divisibilidade.
        self.assertIn('MOD', asm)

    def test_exemplo4_soma(self):
        asm, _ = compile_file(self, "examples/exemplo4_soma.f")
        self.assert_basic_shape(asm)
        # Acesso a array (PUSHGP/PADD/LOAD ou STORE 0) para NUMS(I).
        self.assertTrue(any('PUSHGP' in line for line in asm),
                        "Acesso ao array deve usar PUSHGP")

    def test_exemplo5_conversor_subprograma(self):
        asm, _ = compile_file(self, "examples/exemplo5_conversor.f")
        self.assert_basic_shape(asm)
        # Função do utilizador presente, chamada via CALL e retorno via RETURN.
        self.assertIn('CONVRT:', asm, "Label de entrada da função em falta")
        self.assertIn('CALL', asm, "CALL para a função do utilizador em falta")
        self.assertIn('RETURN', asm, "RETURN da função em falta")
        # Layout local: parâmetro N em fp[-2], B em fp[-1], slot retorno fp[-3].
        self.assertIn('PUSHL -2', asm, "Acesso ao parâmetro N pelo offset local")
        self.assertIn('STOREL -3', asm, "Atribuição ao nome da função pelo slot de retorno")
        # Caller faz POP 2 para limpar os argumentos depois do CALL.
        self.assertIn('POP 2', asm)

    def test_exemplo6_subroutine(self):
        asm, _ = compile_file(self, "examples/exemplo6_subrotina.f")
        self.assert_basic_shape(asm)
        self.assertIn('CUBO:', asm, "Label de entrada da subrotina em falta")
        self.assertIn('CALL', asm)
        self.assertIn('RETURN', asm)
        # Subrotina não aloca slot de retorno; a única referência negativa
        # é o parâmetro N em fp[-1]. Não pode haver STOREL -2 ou inferior.
        self.assertNotIn('STOREL -2', asm)


# Smoke-test direto dos passes: sequências mínimas têm de produzir o que se espera.
class TestOptimizerPasses(unittest.TestCase):

    def test_constant_folding_binop(self):
        code = [ir.CONST(2, 'integer'), ir.CONST(3, 'integer'), ir.BINOP('+', 'integer')]
        out = constant_folding(code)
        self.assertEqual(out, [ir.CONST(5, 'integer')])

    def test_constant_folding_relop(self):
        code = [ir.CONST(2, 'integer'), ir.CONST(3, 'integer'), ir.RELOP('.LT.', 'integer')]
        out = constant_folding(code)
        self.assertEqual(out, [ir.CONST(1, 'logical')])

    def test_constant_folding_neg(self):
        code = [ir.CONST(7, 'integer'), ir.NEG('integer')]
        out = constant_folding(code)
        self.assertEqual(out, [ir.CONST(-7, 'integer')])

    def test_algebraic_x_plus_zero(self):
        code = [ir.LOAD('X', 'integer'), ir.CONST(0, 'integer'), ir.BINOP('+', 'integer')]
        out = algebraic_simplification(code)
        self.assertEqual(out, [ir.LOAD('X', 'integer')])

    def test_algebraic_x_times_one(self):
        code = [ir.LOAD('X', 'integer'), ir.CONST(1, 'integer'), ir.BINOP('*', 'integer')]
        out = algebraic_simplification(code)
        self.assertEqual(out, [ir.LOAD('X', 'integer')])

    def test_algebraic_x_times_zero(self):
        code = [ir.LOAD('X', 'integer'), ir.CONST(0, 'integer'), ir.BINOP('*', 'integer')]
        out = algebraic_simplification(code)
        self.assertEqual(out, [ir.CONST(0, 'integer')])

    def test_branch_folding_false_condition(self):
        code = [ir.CONST(0, 'logical'), ir.JZ('L1')]
        out = branch_folding(code)
        self.assertEqual(out, [ir.JUMP('L1')])

    def test_branch_folding_true_condition(self):
        # Condição != 0 → não salta; JZ desaparece.
        code = [ir.CONST(1, 'logical'), ir.JZ('L1')]
        out = branch_folding(code)
        self.assertEqual(out, [])

    def test_dead_code_after_jump(self):
        code = [ir.JUMP('L'), ir.LOAD('X', 'integer'), ir.WRITE('integer'), ir.LABEL('L')]
        out = dead_code_elimination(code)
        self.assertEqual(out, [ir.JUMP('L'), ir.LABEL('L')])

    def test_dead_code_after_return(self):
        code = [ir.RETURN(), ir.LOAD('X', 'integer'), ir.LABEL('END')]
        out = dead_code_elimination(code)
        self.assertEqual(out, [ir.RETURN(), ir.LABEL('END')])

    def test_jump_threading_drop_jump_to_next(self):
        code = [ir.JUMP('L'), ir.LABEL('L'), ir.HALT()]
        out = jump_threading(code)
        self.assertEqual(out, [ir.LABEL('L'), ir.HALT()])

    def test_jump_threading_collapse_consecutive_labels(self):
        # JUMP A com A: B: ...  →  B é coalesced em A.
        code = [ir.JUMP('B'), ir.HALT(), ir.LABEL('A'), ir.LABEL('B'), ir.HALT()]
        out = jump_threading(code)
        # LABEL B é absorvida por A; JUMP B passa a JUMP A.
        self.assertEqual(out, [ir.JUMP('A'), ir.HALT(), ir.LABEL('A'), ir.HALT()])

    def test_remove_unused_labels(self):
        code = [ir.LOAD('X', 'integer'), ir.LABEL('UNUSED'), ir.HALT()]
        out = remove_unused_labels(code)
        self.assertEqual(out, [ir.LOAD('X', 'integer'), ir.HALT()])

    def test_full_pipeline_idempotent_on_clean_code(self):
        code = [ir.LOAD('X', 'integer'), ir.WRITE('integer'), ir.HALT()]
        self.assertEqual(optimize(code), code)


# Pipeline com optimizador ligado deve continuar a produzir código correcto
# para todos os exemplos.
class TestOptimizedExamples(unittest.TestCase):

    def test_all_examples_compile_with_optimizer(self):
        examples = [
            "examples/exemplo1_hello.f",
            "examples/exemplo2_fatorial.f",
            "examples/exemplo3_primo.f",
            "examples/exemplo4_soma.f",
            "examples/exemplo5_conversor.f",
        ]
        for ex in examples:
            with self.subTest(ex=ex):
                asm, _ = compile_file(self, ex)  # passes default
                self.assertEqual(asm[0], 'start')
                self.assertIn('stop', asm)


if __name__ == '__main__':
    unittest.main()
