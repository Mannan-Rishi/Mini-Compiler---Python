from compiler.ast_nodes import *

class Scope:
    """Represents a symbol table for a single scope level (nested lexical scoping)."""
    def __init__(self, parent=None, name="Global"):
        self.records = {}
        self.parent = parent
        self.name = name

    def declare(self, name: str, type_name: str, line: int) -> bool:
        """Declares a variable in the current scope. Returns False if already declared."""
        if name in self.records:
            return False
        self.records[name] = {"type": type_name, "line": line}
        return True

    def lookup(self, name: str) -> dict:
        """Looks up a variable in this scope or any parent scope (bubble up)."""
        scope = self
        while scope:
            if name in scope.records:
                return scope.records[name]
            scope = scope.parent
        return None


class SemanticAnalyzer:
    """
    Semantic Analyzer for the Mini Compiler.
    Traverses the AST, builds and manages nested symbol tables,
    and performs compile-time validation (scoping, type checking).
    """
    def __init__(self):
        self.errors = []
        self.symbol_table_list = [] # Flattened list of declarations for the UI
        self.current_scope = Scope(parent=None, name="Global")
        self.scope_level = 0
        self.functions = {}
        self.current_function_return_type = None

    def push_scope(self, scope_name: str):
        """Pushes a new nested scope."""
        self.scope_level += 1
        self.current_scope = Scope(parent=self.current_scope, name=f"{scope_name} (Lvl {self.scope_level})")

    def pop_scope(self):
        """Pops back to the parent scope."""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def log_error(self, message: str, line: int):
        """Logs a semantic error."""
        self.errors.append({
            "message": message,
            "line": line,
            "type": "Error"
        })

    def analyze(self, ast_root: ProgramNode):
        """Main entry point to perform semantic analysis on the AST."""
        self.visit(ast_root)
        return self.errors, self.symbol_table_list

    def visit(self, node: ASTNode):
        """Dynamic visitor dispatcher."""
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode):
        """Fallback for unhandled node types."""
        raise Exception(f"No visit_{type(node).__name__} method defined in SemanticAnalyzer.")

    def visit_ProgramNode(self, node: ProgramNode):
        for stmt in node.statements:
            self.visit(stmt)
        return None

    def visit_BlockNode(self, node: BlockNode):
        self.push_scope("Block")
        for stmt in node.statements:
            self.visit(stmt)
        self.pop_scope()
        return None

    def visit_VarDeclNode(self, node: VarDeclNode):
        # 1. Check for duplicate declaration in the current local scope
        success = self.current_scope.declare(node.var_name, node.type_name, node.line)
        if not success:
            self.log_error(f"Duplicate declaration of variable '{node.var_name}' in the same scope.", node.line)
        else:
            # Add to symbol table list for visualization in UI
            self.symbol_table_list.append({
                "name": node.var_name,
                "type": node.type_name,
                "scope": self.current_scope.name,
                "line": node.line
            })

        # 2. Check initial expression if present
        if node.init_expr:
            init_type = self.visit(node.init_expr)
            if init_type:
                # Type checking: cannot assign float to int
                if node.type_name == "int" and init_type == "float":
                    self.log_error(
                        f"Type mismatch: cannot initialize int variable '{node.var_name}' with float expression.",
                        node.line
                    )
        return None

    def visit_AssignNode(self, node: AssignNode):
        # 1. Verify if variable is declared
        var_info = self.current_scope.lookup(node.var_name)
        if not var_info:
            self.log_error(f"Undeclared variable '{node.var_name}' used in assignment.", node.line)
            var_type = None
        else:
            var_type = var_info["type"]

        # 2. Evaluate expression type
        expr_type = self.visit(node.expr)

        # 3. Perform type checking
        if var_type and expr_type:
            if var_type == "int" and expr_type == "float":
                self.log_error(
                    f"Type mismatch: cannot assign float expression to int variable '{node.var_name}'.",
                    node.line
                )
        return None

    def visit_IfNode(self, node: IfNode):
        self.visit(node.condition)
        self.visit(node.then_block)
        if node.else_block:
            self.visit(node.else_block)
        return None

    def visit_WhileNode(self, node: WhileNode):
        self.visit(node.condition)
        self.visit(node.body)
        return None

    def visit_ForNode(self, node: ForNode):
        # A 'for' loop initialization variable is scoped inside the loop itself
        self.push_scope("ForLoop")
        
        self.visit(node.init_stmt)
        self.visit(node.condition)
        self.visit(node.update_stmt)
        self.visit(node.body)
        
        self.pop_scope()
        return None

    def visit_BinOpNode(self, node: BinOpNode) -> str:
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)

        if not left_type or not right_type:
            return None

        # Relational operations: output is boolean-like 'int' (0 or 1) in C-like environments
        if node.op in ('==', '!=', '<', '>', '<=', '>='):
            return "int"

        # Arithmetic operations: promote to float if either operand is float
        if left_type == "float" or right_type == "float":
            return "float"

        return "int"

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> str:
        return self.visit(node.expr)

    def visit_NumNode(self, node: NumNode) -> str:
        return node.type_name

    def visit_VarNode(self, node: VarNode) -> str:
        var_info = self.current_scope.lookup(node.name)
        if not var_info:
            self.log_error(f"Undeclared variable '{node.name}' used in expression.", node.line)
            return None
        return var_info["type"]

    # --- Function Support Methods ---
    def visit_FuncDeclNode(self, node: FuncDeclNode):
        if node.name in self.functions:
            self.log_error(f"Duplicate declaration of function '{node.name}'.", node.line)
        else:
            self.functions[node.name] = {
                "return_type": node.return_type,
                "params": [{"type": p.type_name, "name": p.var_name} for p in node.params]
            }
        
        # Functions are declared globally, but push a function scope for parameters and body
        self.push_scope(f"Function {node.name}")
        old_return_type = self.current_function_return_type
        self.current_function_return_type = node.return_type

        for p in node.params:
            self.visit(p)

        self.visit(node.body)

        self.current_function_return_type = old_return_type
        self.pop_scope()
        return None

    def visit_ParamNode(self, node: ParamNode):
        success = self.current_scope.declare(node.var_name, node.type_name, node.line)
        if not success:
            self.log_error(f"Duplicate declaration of parameter '{node.var_name}'.", node.line)
        else:
            self.symbol_table_list.append({
                "name": node.var_name,
                "type": node.type_name,
                "scope": self.current_scope.name,
                "line": node.line
            })
        return None

    def visit_ReturnNode(self, node: ReturnNode):
        if self.current_function_return_type is None:
            self.log_error("Return statement outside of any function.", node.line)
            return None

        expr_type = "void"
        if node.expr:
            expr_type = self.visit(node.expr)

        # Type checking:
        if self.current_function_return_type == "void":
            if expr_type != "void":
                self.log_error("Function declared as void cannot return a value.", node.line)
        elif self.current_function_return_type == "int":
            if expr_type == "float":
                self.log_error("Type mismatch: cannot return float value from an int function.", node.line)
            elif expr_type == "void":
                self.log_error("Function declared as int must return a value.", node.line)
        elif self.current_function_return_type == "float":
            if expr_type == "void":
                self.log_error("Function declared as float must return a value.", node.line)
        return None

    def visit_FuncCallNode(self, node: FuncCallNode) -> str:
        if node.name not in self.functions:
            self.log_error(f"Undeclared function '{node.name}' called.", node.line)
            return "int"  # fallback type to allow compilation to proceed

        func_info = self.functions[node.name]
        expected_params = func_info["params"]
        
        if len(node.args) != len(expected_params):
            self.log_error(f"Function '{node.name}' expects {len(expected_params)} arguments, but {len(node.args)} were given.", node.line)
        else:
            for idx, arg in enumerate(node.args):
                arg_type = self.visit(arg)
                param_type = expected_params[idx]["type"]
                if param_type == "int" and arg_type == "float":
                    self.log_error(f"Type mismatch on argument {idx+1} of call to '{node.name}': expected int, got float.", node.line)

        return func_info["return_type"]
