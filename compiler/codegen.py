from compiler.ast_nodes import *

class TACInstruction:
    """Represents a single Three-Address Code (TAC) instruction."""
    def __init__(self, op: str, arg1, arg2=None, result=None):
        self.op = op          # Operator (e.g. ADD, ASSIGN, LABEL, IF_FALSE, GOTO, FUNC_BEGIN, FUNC_END, PARAM, CALL, RETURN)
        self.arg1 = arg1      # First operand / target label / source variable
        self.arg2 = arg2      # Second operand (optional)
        self.result = result  # Target variable where result is stored (optional)

    def to_dict(self):
        """Converts instruction fields into a dictionary for JSON output."""
        return {
            "op": self.op,
            "arg1": str(self.arg1) if self.arg1 is not None else "",
            "arg2": str(self.arg2) if self.arg2 is not None else "",
            "result": str(self.result) if self.result is not None else ""
        }

    def __str__(self):
        if self.op == 'ASSIGN':
            return f"{self.result} = {self.arg1}"
        elif self.op in ('ADD', 'SUB', 'MUL', 'DIV', 'EQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'):
            op_symbol = {
                'ADD': '+', 'SUB': '-', 'MUL': '*', 'DIV': '/',
                'EQ': '==', 'NEQ': '!=', 'LT': '<', 'GT': '>', 'LTE': '<=', 'GTE': '>='
            }.get(self.op, self.op)
            return f"{self.result} = {self.arg1} {op_symbol} {self.arg2}"
        elif self.op == 'UNARY_MINUS':
            return f"{self.result} = -{self.arg1}"
        elif self.op == 'LABEL':
            return f"label {self.arg1}"
        elif self.op == 'GOTO':
            return f"goto {self.arg1}"
        elif self.op == 'IF_FALSE':
            return f"ifFalse {self.arg1} goto {self.arg2}"
        elif self.op == 'FUNC_BEGIN':
            return f"func begin {self.arg1}"
        elif self.op == 'FUNC_END':
            return f"func end"
        elif self.op == 'PARAM':
            return f"param {self.arg1}"
        elif self.op == 'CALL':
            if self.result:
                return f"{self.result} = call {self.arg1}, {self.arg2}"
            return f"call {self.arg1}, {self.arg2}"
        elif self.op == 'RETURN':
            if self.arg1 is not None:
                return f"return {self.arg1}"
            return "return"
        return f"{self.result} = {self.op} ({self.arg1}, {self.arg2})"


class TACGenerator:
    """
    Intermediate Code Generator.
    Walks the AST and generates Three-Address Code (TAC).
    """
    def __init__(self):
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0

    def new_temp(self) -> str:
        """Creates a new unique temporary variable."""
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp

    def new_label(self) -> str:
        """Creates a new unique branch label."""
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label

    def emit(self, op: str, arg1, arg2=None, result=None):
        """Appends a TAC instruction to the listing."""
        instr = TACInstruction(op, arg1, arg2, result)
        self.instructions.append(instr)

    def generate(self, ast_root: ProgramNode) -> list:
        """Translates the AST and returns a list of TAC instructions."""
        self.visit(ast_root)
        return self.instructions

    def visit(self, node: ASTNode):
        """Dynamic visitor dispatcher."""
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode):
        raise Exception(f"No visit_{type(node).__name__} method defined in TACGenerator.")

    def visit_ProgramNode(self, node: ProgramNode):
        for stmt in node.statements:
            self.visit(stmt)
        return None

    def visit_BlockNode(self, node: BlockNode):
        for stmt in node.statements:
            self.visit(stmt)
        return None

    def visit_VarDeclNode(self, node: VarDeclNode):
        if node.init_expr:
            expr_val = self.visit(node.init_expr)
            self.emit('ASSIGN', expr_val, None, node.var_name)
        return None

    def visit_AssignNode(self, node: AssignNode):
        expr_val = self.visit(node.expr)
        self.emit('ASSIGN', expr_val, None, node.var_name)
        return node.var_name

    def visit_IfNode(self, node: IfNode):
        L_else = self.new_label()
        L_end = self.new_label()

        # 1. Condition evaluation
        cond_val = self.visit(node.condition)
        
        # 2. Conditional jump
        self.emit('IF_FALSE', cond_val, L_else)

        # 3. Then block
        self.visit(node.then_block)
        
        if node.else_block:
            self.emit('GOTO', L_end)
            self.emit('LABEL', L_else)
            self.visit(node.else_block)
            self.emit('LABEL', L_end)
        else:
            self.emit('LABEL', L_else)
        return None

    def visit_WhileNode(self, node: WhileNode):
        L_cond = self.new_label()
        L_end = self.new_label()

        # 1. Condition label
        self.emit('LABEL', L_cond)

        # 2. Condition evaluation
        cond_val = self.visit(node.condition)

        # 3. Exit condition check
        self.emit('IF_FALSE', cond_val, L_end)

        # 4. Body statements
        self.visit(node.body)

        # 5. Loop back
        self.emit('GOTO', L_cond)
        self.emit('LABEL', L_end)
        return None

    def visit_ForNode(self, node: ForNode):
        L_cond = self.new_label()
        L_end = self.new_label()

        # 1. Loop Init statement
        if node.init_stmt:
            self.visit(node.init_stmt)

        # 2. Condition check label
        self.emit('LABEL', L_cond)

        # 3. Condition check evaluation
        if node.condition:
            cond_val = self.visit(node.condition)
            self.emit('IF_FALSE', cond_val, L_end)

        # 4. Loop Body
        self.visit(node.body)

        # 5. Update statement
        if node.update_stmt:
            self.visit(node.update_stmt)

        # 6. Jump back
        self.emit('GOTO', L_cond)
        self.emit('LABEL', L_end)
        return None

    def visit_BinOpNode(self, node: BinOpNode) -> str:
        left_val = self.visit(node.left)
        right_val = self.visit(node.right)

        op_map = {
            '+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV',
            '==': 'EQ', '!=': 'NEQ', '<': 'LT', '>': 'GT', '<=': 'LTE', '>=': 'GTE'
        }
        op_code = op_map.get(node.op, node.op)
        temp = self.new_temp()
        self.emit(op_code, left_val, right_val, temp)
        return temp

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> str:
        expr_val = self.visit(node.expr)
        temp = self.new_temp()
        self.emit('UNARY_MINUS', expr_val, None, temp)
        return temp

    def visit_NumNode(self, node: NumNode) -> str:
        return str(node.value)

    def visit_VarNode(self, node: VarNode) -> str:
        return node.name

    # --- Function Support visitor methods ---
    def visit_FuncDeclNode(self, node: FuncDeclNode):
        self.emit('FUNC_BEGIN', node.name)
        self.visit(node.body)
        self.emit('FUNC_END', node.name)
        return None

    def visit_ParamNode(self, node: ParamNode):
        # Param is a declaration helper, no TAC instruction emitted at decl time
        return None

    def visit_ReturnNode(self, node: ReturnNode):
        val = None
        if node.expr:
            val = self.visit(node.expr)
        self.emit('RETURN', val)
        return None

    def visit_FuncCallNode(self, node: FuncCallNode) -> str:
        # 1. Emit PARAM instructions for each argument
        for arg in node.args:
            val = self.visit(arg)
            self.emit('PARAM', val)
        
        # 2. Emit CALL instruction
        temp = self.new_temp()
        self.emit('CALL', node.name, len(node.args), temp)
        return temp
