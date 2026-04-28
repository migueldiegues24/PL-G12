import unittest
import os

from syntax_analysis.lexer import lexer
from syntax_analysis.parser import parser
from semantic_analysis.analyser import SemanticAnalyser


# Análise semântica dos 5 exemplos do enunciado: nenhum deve produzir erros.
class TestSemanticExamples(unittest.TestCase):

    def analyse_file(self, filepath):
        self.assertTrue(os.path.exists(filepath), f"Ficheiro não encontrado: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            codigo = f.read()
        lexer.lineno = 1
        ast = parser.parse(codigo, lexer=lexer)
        self.assertIsNotNone(ast, "Parser devolveu None — erro sintático.")
        analyser = SemanticAnalyser()
        annotated, table, reporter = analyser.analyse(ast)
        return annotated, table, reporter

    def test_exemplo1_hello_sem_erros(self):
        _, _, r = self.analyse_file("examples/exemplo1_hello.f")
        self.assertEqual(r.count(), 0, f"Erros inesperados: {[e.message for e in r.errors]}")

    def test_exemplo2_fatorial_sem_erros(self):
        _, _, r = self.analyse_file("examples/exemplo2_fatorial.f")
        self.assertEqual(r.count(), 0, f"Erros inesperados: {[e.message for e in r.errors]}")

    def test_exemplo3_primo_sem_erros(self):
        _, _, r = self.analyse_file("examples/exemplo3_primo.f")
        self.assertEqual(r.count(), 0, f"Erros inesperados: {[e.message for e in r.errors]}")

    def test_exemplo4_soma_sem_erros(self):
        _, _, r = self.analyse_file("examples/exemplo4_soma.f")
        self.assertEqual(r.count(), 0, f"Erros inesperados: {[e.message for e in r.errors]}")

    def test_exemplo5_conversor_sem_erros(self):
        _, _, r = self.analyse_file("examples/exemplo5_conversor.f")
        self.assertEqual(r.count(), 0, f"Erros inesperados: {[e.message for e in r.errors]}")


# Helper para criar e correr o analisador a partir de uma string.
def analyse(code):
    lexer.lineno = 1
    ast = parser.parse(code, lexer=lexer)
    if ast is None:
        return None, None, None
    a = SemanticAnalyser()
    return a.analyse(ast)


# Deteção de erros semânticos — cada teste constrói um programa pequeno
# que viola uma regra específica e verifica que o reporter regista o erro.
class TestSemanticErrors(unittest.TestCase):

    def assert_has_error(self, reporter, substring):
        msgs = [e.message for e in reporter.errors]
        self.assertTrue(
            any(substring in m for m in msgs),
            f"Esperava erro contendo '{substring}', mensagens={msgs}"
        )

    def test_variavel_nao_declarada(self):
        code = "      PROGRAM T\n      X = 5\n      END\n"
        _, _, r = analyse(code)
        self.assert_has_error(r, "não declarada")

    def test_atribuicao_incompativel(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      LOGICAL Y\n"
            "      Y = .TRUE.\n"
            "      X = Y\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "Atribuição incompatível")

    def test_promocao_integer_para_real(self):
        # Atribuir integer a real é permitido em Fortran 77.
        code = (
            "      PROGRAM T\n"
            "      REAL R\n"
            "      INTEGER I\n"
            "      I = 5\n"
            "      R = I\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assertEqual(r.count(), 0, f"Erros inesperados: {[e.message for e in r.errors]}")

    def test_if_condicao_nao_logical(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      X = 5\n"
            "      IF (X) THEN\n"
            "        X = 1\n"
            "      ENDIF\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "logical")

    def test_indice_array_nao_integer(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER A(5)\n"
            "      REAL R\n"
            "      R = 1.5\n"
            "      A(R) = 0\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "ndice")

    def test_variavel_do_real(self):
        code = (
            "      PROGRAM T\n"
            "      REAL I\n"
            "      DO 10 I = 1, 5\n"
            "   10 CONTINUE\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "DO")

    def test_label_indefinida(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      X = 0\n"
            "      GOTO 99\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "Label 99")

    def test_redeclaracao_variavel(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      INTEGER X\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "já declarada")

    def test_funcao_aridade_errada(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X, Y\n"
            "      X = 5\n"
            "      Y = MOD(X)\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "MOD")

    def test_array_sem_indice_em_atribuicao(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER A(5)\n"
            "      A = 10\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "ndice")

    def test_chamada_a_variavel(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X, Y\n"
            "      X = 5\n"
            "      Y = X(1)\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "não é função nem array")

    def test_label_duplicada(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER I\n"
            "   10 I = 1\n"
            "   10 I = 2\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "duplicada")

    def test_not_sobre_inteiro(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      LOGICAL Y\n"
            "      X = 1\n"
            "      Y = .NOT. X\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "NOT")

    def test_and_sobre_inteiros(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X, Y\n"
            "      LOGICAL R\n"
            "      X = 1\n"
            "      Y = 2\n"
            "      R = X .AND. Y\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "logical")

    def test_uso_antes_de_inicializar(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X, Y\n"
            "      Y = X + 1\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "inicializada")

    def test_subrotina_aridade_errada(self):
        code = (
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      X = 5\n"
            "      CALL FOO(X)\n"
            "      END\n"
            "\n"
            "      SUBROUTINE FOO(A, B)\n"
            "      INTEGER A, B\n"
            "      A = B\n"
            "      RETURN\n"
            "      END\n"
        )
        _, _, r = analyse(code)
        self.assert_has_error(r, "FOO")


# Anotações de tipo na AST devolvida pelo analyser.
class TestSemanticAnnotations(unittest.TestCase):

    def test_num_inteiro_anotado(self):
        annotated, _, _ = analyse(
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      X = 42\n"
            "      END\n"
        )
        body = annotated[1][0][2][1]                 # main_program → body → items
        assign = next(it for it in body if it[0] == 'assign')
        rhs = assign[2]
        self.assertEqual(rhs[0], 'num')
        self.assertEqual(rhs[-1], {'type': 'integer'})

    def test_num_real_anotado(self):
        annotated, _, _ = analyse(
            "      PROGRAM T\n"
            "      REAL R\n"
            "      R = 3.14\n"
            "      END\n"
        )
        body = annotated[1][0][2][1]
        assign = next(it for it in body if it[0] == 'assign')
        rhs = assign[2]
        self.assertEqual(rhs[-1], {'type': 'real'})

    def test_bool_anotado(self):
        annotated, _, _ = analyse(
            "      PROGRAM T\n"
            "      LOGICAL B\n"
            "      B = .TRUE.\n"
            "      END\n"
        )
        body = annotated[1][0][2][1]
        assign = next(it for it in body if it[0] == 'assign')
        self.assertEqual(assign[2][-1], {'type': 'logical'})

    def test_binop_promocao_para_real(self):
        annotated, _, _ = analyse(
            "      PROGRAM T\n"
            "      REAL R\n"
            "      INTEGER I\n"
            "      I = 2\n"
            "      R = I + 1.5\n"
            "      END\n"
        )
        body = annotated[1][0][2][1]
        assign = [it for it in body if it[0] == 'assign'][1]
        rhs = assign[2]
        self.assertEqual(rhs[0], 'binop')
        self.assertEqual(rhs[-1], {'type': 'real'})

    def test_relop_devolve_logical(self):
        annotated, _, _ = analyse(
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      LOGICAL Y\n"
            "      X = 5\n"
            "      Y = X .GT. 0\n"
            "      END\n"
        )
        body = annotated[1][0][2][1]
        assign = [it for it in body if it[0] == 'assign'][1]
        self.assertEqual(assign[2][0], 'relop')
        self.assertEqual(assign[2][-1], {'type': 'logical'})

    def test_call_or_array_resolve_em_call(self):
        annotated, _, _ = analyse(
            "      PROGRAM T\n"
            "      INTEGER X, Y\n"
            "      X = 7\n"
            "      Y = MOD(X, 3)\n"
            "      END\n"
        )
        body = annotated[1][0][2][1]
        assign = [it for it in body if it[0] == 'assign'][1]
        self.assertEqual(assign[2][0], 'call')
        self.assertEqual(assign[2][1], 'MOD')
        self.assertEqual(assign[2][-1], {'type': 'integer'})

    def test_call_or_array_resolve_em_index(self):
        annotated, _, _ = analyse(
            "      PROGRAM T\n"
            "      INTEGER A(5), I, X\n"
            "      I = 1\n"
            "      A(I) = 10\n"
            "      X = A(I)\n"
            "      END\n"
        )
        body = annotated[1][0][2][1]
        assigns = [it for it in body if it[0] == 'assign']
        last = assigns[-1]
        self.assertEqual(last[2][0], 'index')
        self.assertEqual(last[2][1], 'A')
        self.assertEqual(last[2][-1], {'type': 'integer'})


# Estado da tabela de símbolos após a análise.
class TestSemanticSymbolTable(unittest.TestCase):

    def test_funcoes_intrinsecas_no_global(self):
        a = SemanticAnalyser()
        sym = a.table.lookup('MOD')
        self.assertEqual(sym.kind, 'function')
        self.assertEqual(sym.type, 'integer')
        self.assertEqual(len(sym.params), 2)

    def test_funcao_utilizador_registada(self):
        _, table, _ = analyse(
            "      PROGRAM T\n"
            "      INTEGER X\n"
            "      X = 0\n"
            "      END\n"
            "\n"
            "      INTEGER FUNCTION DOBRO(N)\n"
            "      INTEGER N\n"
            "      DOBRO = N + N\n"
            "      RETURN\n"
            "      END\n"
        )
        sym = table.lookup_global('DOBRO')
        self.assertIsNotNone(sym)
        self.assertEqual(sym.kind, 'function')
        self.assertEqual(sym.type, 'integer')
        # Tipo do parâmetro foi inferido a partir da declaração no corpo.
        self.assertEqual(sym.params, ['integer'])

    def test_array_inicializado_via_read(self):
        _, table, r = analyse(
            "      PROGRAM T\n"
            "      INTEGER A(3), I\n"
            "      DO 10 I = 1, 3\n"
            "        READ *, A(I)\n"
            "   10 CONTINUE\n"
            "      END\n"
        )
        self.assertEqual(r.count(), 0)
        # Após pop_scope o scope global persiste — confirmar que o programa correu.
        self.assertEqual(table.current_scope_name, 'global')


if __name__ == '__main__':
    unittest.main()
