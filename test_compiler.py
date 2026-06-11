import unittest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import SemanticAnalyzer
from compiler.codegen import TACGenerator
from compiler.optimizer import TACOptimizer
from compiler.target_codegen import TargetCodeGenerator

class TestCompilerPhases(unittest.TestCase):

    def test_lexer_tokenization(self):
        """Test that the lexer identifies C-like keywords, numbers, and operators correctly."""
        code = "int x = 10; float y = 3.14; if (x > y) {}"
        lexer = Lexer(code)
        tokens = lexer.get_tokens()
        errors = lexer.get_errors()

        self.assertEqual(len(errors), 0, f"Lexer errors found: {errors}")
        
        # Verify specific tokens are recognized
        types = [t['type'] for t in tokens]
        values = [t['value'] for t in tokens]
        
        self.assertIn('KEYWORD', types)
        self.assertIn('ID', types)
        self.assertIn('ASSIGN', types)
        self.assertIn('INT', types)
        self.assertIn('FLOAT', types)
        
        self.assertEqual(values[0], 'int')
        self.assertEqual(values[1], 'x')
        self.assertEqual(values[3], '10')
        self.assertEqual(values[4], ';')

    def test_lexer_invalid_character(self):
        """Test that unexpected characters are captured as lexical errors."""
        code = "int x = 5 @ 10;"
        lexer = Lexer(code)
        errors = lexer.get_errors()
        
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['message'], "Unexpected character '@'")
        self.assertEqual(errors[0]['line'], 1)

    def test_parser_arithmetic_precedence(self):
        """Test parser correctly parses binary expressions respecting operator precedence."""
        code = "int res = 2 + 3 * 4;"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        self.assertEqual(len(parser.errors), 0)
        self.assertIsNotNone(ast)
        
        # Expected AST structure:
        # ProgramNode -> VarDeclNode -> BinOpNode(+, 2, BinOpNode(*, 3, 4))
        self.assertEqual(ast.statements[0].var_name, "res")
        init_expr = ast.statements[0].init_expr
        self.assertEqual(init_expr.op, "+")
        self.assertEqual(init_expr.left.value, 2)
        self.assertEqual(init_expr.right.op, "*")
        self.assertEqual(init_expr.right.left.value, 3)
        self.assertEqual(init_expr.right.right.value, 4)

    def test_parser_for_loop(self):
        """Test parser parses C-like for loops correctly."""
        code = "for (int i = 0; i < 5; i = i + 1) { x = i; }"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        self.assertEqual(len(parser.errors), 0)
        self.assertIsNotNone(ast)
        self.assertEqual(ast.statements[0].to_dict()['type'], "ForLoop")

    def test_semantic_undeclared_variable(self):
        """Test semantic analyzer detects use of undeclared variables."""
        code = "int a = 5; b = a + 2;"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        semantic_analyzer = SemanticAnalyzer()
        errors, symbol_table = semantic_analyzer.analyze(ast)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("Undeclared variable 'b'", errors[0]['message'])

    def test_semantic_duplicate_declaration(self):
        """Test semantic analyzer detects duplicate variable declarations within same scope."""
        code = "int x = 5; float x = 2.0;"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        semantic_analyzer = SemanticAnalyzer()
        errors, symbol_table = semantic_analyzer.analyze(ast)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("Duplicate declaration of variable 'x'", errors[0]['message'])

    def test_semantic_type_mismatch(self):
        """Test semantic analyzer flags assignment of float expressions to int variables."""
        code = "int a; float b = 3.14; a = b;"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        semantic_analyzer = SemanticAnalyzer()
        errors, symbol_table = semantic_analyzer.analyze(ast)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("Type mismatch: cannot assign float expression to int variable 'a'", errors[0]['message'])

    def test_optimizer_constant_folding(self):
        """Test optimizer folds constant arithmetic operations."""
        code = "int val = 2 + 3 * 4;"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        tac_generator = TACGenerator()
        tac = tac_generator.generate(ast)
        
        # Verify pre-optimized instructions contain arithmetic operations
        ops_pre = [i.op for i in tac]
        self.assertTrue('ADD' in ops_pre)
        self.assertTrue('MUL' in ops_pre)
        
        # Run optimizer
        optimizer = TACOptimizer(tac)
        optimized_tac = optimizer.optimize()
        
        # After optimization, it should fold 2 + 3 * 4 to 14, leaving just a simple assign: val = 14
        ops_post = [i.op for i in optimized_tac]
        self.assertEqual(len(optimized_tac), 1)
        self.assertEqual(optimized_tac[0].op, 'ASSIGN')
        self.assertEqual(optimized_tac[0].arg1, '14')
        self.assertEqual(optimized_tac[0].result, 'val')

    def test_optimizer_dead_code_elimination(self):
        """Test optimizer removes dead temporary variable assignments."""
        # x = 2 + 3; y = x * 4;
        # Generates:
        # t0 = 2 + 3 (folded to t0 = 5)
        # x = t0     (propagated to x = 5)
        # t1 = x * 4 (propagated/folded to t1 = 20)
        # y = t1     (propagated to y = 20)
        # Dead Code Elimination removes t0 = 5 and t1 = 20 because they are never read downstream!
        code = "int x; int y; x = 2 + 3; y = x * 4;"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        tac_generator = TACGenerator()
        tac = tac_generator.generate(ast)
        
        optimizer = TACOptimizer(tac)
        optimized_tac = optimizer.optimize()
        
        # Should result in:
        # x = 5
        # y = 20
        self.assertEqual(len(optimized_tac), 2)
        self.assertEqual(optimized_tac[0].result, 'x')
        self.assertEqual(optimized_tac[0].arg1, '5')
        self.assertEqual(optimized_tac[1].result, 'y')
        self.assertEqual(optimized_tac[1].arg1, '20')

    def test_target_codegen(self):
        """Test target code generator translates optimized TAC instructions to pseudo-assembly."""
        code = "int a = 5 + 10;"
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        
        tac = TACGenerator().generate(ast)
        opt_tac = TACOptimizer(tac).optimize()
        
        assembly = TargetCodeGenerator(opt_tac).generate()
        
        # Assembly for optimized 'a = 15' should load 15 and store into a
        # Filter comments and empty lines
        instructions = [line for line in assembly if line.strip() and not line.startswith(';')]
        
        self.assertEqual(len(instructions), 2)
        self.assertEqual(instructions[0], "LOAD  15")
        self.assertEqual(instructions[1], "STORE a")

    def test_functions_compilation(self):
        """Test parsing, semantics, and code generation for function declarations and calls."""
        code = """
        int add(int x, int y) {
            return x + y;
        }
        int main() {
            int a = 10;
            int b = add(a, 5);
        }
        """
        lexer = Lexer(code)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        self.assertEqual(len(parser.errors), 0)

        semantic_analyzer = SemanticAnalyzer()
        errors, symbol_table = semantic_analyzer.analyze(ast)
        self.assertEqual(len(errors), 0)

        # Verify function parameter symbol table entries
        param_entries = [entry for entry in symbol_table if entry['scope'].startswith("Function add")]
        self.assertEqual(len(param_entries), 2)
        self.assertEqual(param_entries[0]['name'], 'x')
        self.assertEqual(param_entries[1]['name'], 'y')

        # Generate intermediate code
        tac = TACGenerator().generate(ast)
        opt_tac = TACOptimizer(tac).optimize()

        # Check for function entry/exit, param, call and return opcodes
        ops = [inst.op for inst in opt_tac]
        self.assertIn('FUNC_BEGIN', ops)
        self.assertIn('FUNC_END', ops)
        self.assertIn('PARAM', ops)
        self.assertIn('CALL', ops)
        self.assertIn('RETURN', ops)

if __name__ == '__main__':
    unittest.main()
