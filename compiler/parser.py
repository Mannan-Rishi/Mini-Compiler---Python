from compiler.ast_nodes import *

class Parser:
    """
    Recursive Descent Parser for the Mini Compiler.
    Parses a list of tokens and builds an Abstract Syntax Tree (AST).
    Collects syntax errors and recovers using a synchronize mechanism.

    Function support is intentionally limited:
      - Simple declarations: int/float/void funcname(params) { body }
      - Return statements inside function bodies
      - Function calls as primary expressions in assignments/declarations
      - No recursion detection, overloading, or nested function definitions
    """
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        self.current_token = self.tokens[self.pos] if self.tokens else None

    def advance(self):
        """Advances the token cursor."""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    def expect(self, token_type, value=None):
        """Validates current token and advances, logging an error on mismatch."""
        if self.current_token:
            type_match = self.current_token['type'] == token_type
            value_match = value is None or self.current_token['value'] == value
            if type_match and value_match:
                tok = self.current_token
                self.advance()
                return tok
            else:
                expected_str = f"{token_type}" + (f" ('{value}')" if value else "")
                actual_str = f"{self.current_token['type']} ('{self.current_token['value']}')"
                self.error(f"Expected {expected_str}, found {actual_str}")
                raise SyntaxError(f"Expected {expected_str}")
        else:
            expected_str = f"{token_type}" + (f" ('{value}')" if value else "")
            self.error(f"Expected {expected_str}, found End of File")
            raise SyntaxError(f"Expected {expected_str}")

    def error(self, msg):
        """Logs a syntax error with line and column information."""
        tok = self.current_token if self.current_token else (self.tokens[-1] if self.tokens else {"line": 1, "column": 1})
        self.errors.append({
            "message": msg,
            "line": tok.get("line", 1),
            "column": tok.get("column", 1)
        })

    def synchronize(self):
        """Recovers parser state after an error by skipping to statement boundaries."""
        while self.current_token is not None:
            # Semicolons and closing braces indicate a statement boundary
            if self.current_token['type'] == 'SEMI':
                self.advance()
                return
            if self.current_token['type'] == 'RBRACE':
                return
            # Structural keywords indicate a new statement
            if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] in ('int', 'float', 'void', 'if', 'while', 'for', 'return'):
                return
            self.advance()

    def _peek_is_func_decl(self) -> bool:
        """
        Lookahead: returns True if current position looks like a function declaration.
        Pattern: KEYWORD(type) ID LPAREN
        """
        if not self.current_token:
            return False
        if self.current_token['type'] != 'KEYWORD':
            return False
        if self.current_token['value'] not in ('int', 'float', 'void'):
            return False
        # Peek ahead two tokens
        next_pos = self.pos + 1
        after_pos = self.pos + 2
        if next_pos >= len(self.tokens) or after_pos >= len(self.tokens):
            return False
        return (self.tokens[next_pos]['type'] == 'ID' and
                self.tokens[after_pos]['type'] == 'LPAREN')

    def parse(self) -> ProgramNode:
        """Parses the full token stream and returns a ProgramNode."""
        statements = []
        while self.current_token is not None:
            try:
                stmt = self.top_level_statement()
                if stmt:
                    statements.append(stmt)
            except SyntaxError:
                self.synchronize()
        return ProgramNode(statements)

    def top_level_statement(self) -> ASTNode:
        """
        Parses top-level items: function declarations take priority over variable declarations.
        Falls back to regular statement parsing for everything else.
        """
        if self._peek_is_func_decl():
            return self.func_declaration()
        return self.statement()

    def statement(self) -> ASTNode:
        """Parses a statement: declaration, assignment, if, while, for, return, block, or empty."""
        if not self.current_token:
            return None

        # Block statement
        if self.current_token['type'] == 'LBRACE':
            return self.block()

        # Variable declaration (non-function — checked via lookahead)
        if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] in ('int', 'float'):
            if not self._peek_is_func_decl():
                return self.declaration()

        # Return statement
        if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'return':
            return self.return_statement()

        # Conditional If statement
        if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'if':
            return self.if_statement()

        # Loop While statement
        if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'while':
            return self.while_statement()

        # Loop For statement
        if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'for':
            return self.for_statement()

        # Assignment statement
        if self.current_token['type'] == 'ID':
            return self.assignment()

        # Empty statement (just a semicolon)
        if self.current_token['type'] == 'SEMI':
            self.advance()
            return None

        # Fallback / Error
        tok = self.current_token
        self.error(f"Unexpected token {tok['type']} ('{tok['value']}')")
        self.advance()
        raise SyntaxError("Unexpected token")

    def block(self) -> BlockNode:
        """Parses a bracketed block of statements: { statement* }"""
        self.expect('LBRACE')
        statements = []
        while self.current_token and self.current_token['type'] != 'RBRACE':
            try:
                stmt = self.statement()
                if stmt:
                    statements.append(stmt)
            except SyntaxError:
                self.synchronize()
        self.expect('RBRACE')
        return BlockNode(statements)

    def declaration(self) -> VarDeclNode:
        """Parses variable declarations: (int|float) x [= expr];"""
        type_tok = self.expect('KEYWORD')
        id_tok = self.expect('ID')
        init_expr = None

        if self.current_token and self.current_token['type'] == 'ASSIGN':
            self.advance()
            init_expr = self.expr()

        self.expect('SEMI')
        node = VarDeclNode(type_tok['value'], id_tok['value'], init_expr)
        node.line = type_tok['line']
        node.column = type_tok['column']
        return node

    def assignment(self) -> AssignNode:
        """Parses variable assignment: x = expr;"""
        id_tok = self.expect('ID')
        self.expect('ASSIGN')
        expr = self.expr()
        self.expect('SEMI')
        node = AssignNode(id_tok['value'], expr)
        node.line = id_tok['line']
        node.column = id_tok['column']
        return node

    def if_statement(self) -> IfNode:
        """Parses conditional statements: if (expr) statement [else statement]"""
        if_tok = self.expect('KEYWORD', 'if')
        self.expect('LPAREN')
        condition = self.expr()
        self.expect('RPAREN')
        then_block = self.statement()
        else_block = None

        if self.current_token and self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'else':
            self.advance()
            else_block = self.statement()

        node = IfNode(condition, then_block, else_block)
        node.line = if_tok['line']
        node.column = if_tok['column']
        return node

    def while_statement(self) -> WhileNode:
        """Parses loops: while (expr) statement"""
        while_tok = self.expect('KEYWORD', 'while')
        self.expect('LPAREN')
        condition = self.expr()
        self.expect('RPAREN')
        body = self.statement()
        node = WhileNode(condition, body)
        node.line = while_tok['line']
        node.column = while_tok['column']
        return node

    def for_statement(self) -> ForNode:
        """Parses loops: for (init; cond; update) statement"""
        for_tok = self.expect('KEYWORD', 'for')
        self.expect('LPAREN')

        # 1. Initialization statement
        init_stmt = None
        if self.current_token and self.current_token['type'] == 'KEYWORD' and self.current_token['value'] in ('int', 'float'):
            init_stmt = self.declaration()  # This consumes the semicolon
        elif self.current_token and self.current_token['type'] == 'ID':
            init_stmt = self.assignment()   # This consumes the semicolon
        else:
            self.expect('SEMI')             # Empty init

        # 2. Loop Condition
        condition = None
        if self.current_token and self.current_token['type'] != 'SEMI':
            condition = self.expr()
        self.expect('SEMI')

        # 3. Loop Update expression (reassignment without trailing semicolon)
        update_stmt = None
        if self.current_token and self.current_token['type'] != 'RPAREN':
            id_tok = self.expect('ID')
            self.expect('ASSIGN')
            update_expr = self.expr()
            update_stmt = AssignNode(id_tok['value'], update_expr)
            update_stmt.line = id_tok['line']
            update_stmt.column = id_tok['column']

        self.expect('RPAREN')
        body = self.statement()

        node = ForNode(init_stmt, condition, update_stmt, body)
        node.line = for_tok['line']
        node.column = for_tok['column']
        return node

    def return_statement(self) -> ReturnNode:
        """Parses: return [expr];"""
        ret_tok = self.expect('KEYWORD', 'return')
        expr = None
        if self.current_token and self.current_token['type'] != 'SEMI':
            expr = self.expr()
        self.expect('SEMI')
        node = ReturnNode(expr)
        node.line = ret_tok['line']
        node.column = ret_tok['column']
        return node

    def func_declaration(self) -> FuncDeclNode:
        """
        Parses a function declaration:
            (int|float|void) funcname ( [param, ...] ) { body }
        """
        type_tok = self.expect('KEYWORD')   # int / float / void
        name_tok = self.expect('ID')
        self.expect('LPAREN')

        params = []
        while self.current_token and self.current_token['type'] != 'RPAREN':
            pt = self.expect('KEYWORD')     # int or float
            pn = self.expect('ID')
            p = ParamNode(pt['value'], pn['value'])
            p.line = pt['line']
            p.column = pt['column']
            params.append(p)
            # Consume comma between params
            if self.current_token and self.current_token['type'] == 'COMMA':
                self.advance()

        self.expect('RPAREN')
        body = self.block()

        node = FuncDeclNode(type_tok['value'], name_tok['value'], params, body)
        node.line = type_tok['line']
        node.column = type_tok['column']
        return node

    def expr(self) -> ASTNode:
        """Parses expressions (maps to lowest precedence: relations)."""
        return self.relation()

    def relation(self) -> ASTNode:
        """Parses relational comparison expressions (==, !=, <, >, <=, >=)."""
        node = self.add_sub()
        rel_ops = ('EQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE')
        while self.current_token and self.current_token['type'] in rel_ops:
            op_tok = self.current_token
            op = op_tok['value']
            self.advance()
            right = self.add_sub()
            node = BinOpNode(node, op, right)
            node.line = op_tok['line']
            node.column = op_tok['column']
        return node

    def add_sub(self) -> ASTNode:
        """Parses addition and subtraction expressions (+, -)."""
        node = self.term()
        while self.current_token and self.current_token['type'] in ('PLUS', 'MINUS'):
            op_tok = self.current_token
            op = op_tok['value']
            self.advance()
            right = self.term()
            node = BinOpNode(node, op, right)
            node.line = op_tok['line']
            node.column = op_tok['column']
        return node

    def term(self) -> ASTNode:
        """Parses multiplication and division expressions (*, /)."""
        node = self.factor()
        while self.current_token and self.current_token['type'] in ('MUL', 'DIV'):
            op_tok = self.current_token
            op = op_tok['value']
            self.advance()
            right = self.factor()
            node = BinOpNode(node, op, right)
            node.line = op_tok['line']
            node.column = op_tok['column']
        return node

    def factor(self) -> ASTNode:
        """Parses variables, literal numbers, unary negation, function calls, or parenthesized expressions."""
        if not self.current_token:
            self.error("Unexpected end of expression")
            raise SyntaxError("Unexpected EOF")

        tok = self.current_token

        # Unary Negation
        if tok['type'] == 'MINUS':
            self.advance()
            fact = self.factor()
            node = UnaryOpNode('-', fact)
            node.line = tok['line']
            node.column = tok['column']
            return node

        # Integer literal
        if tok['type'] == 'INT':
            self.advance()
            node = NumNode(int(tok['value']), 'int')
            node.line = tok['line']
            node.column = tok['column']
            return node

        # Float literal
        if tok['type'] == 'FLOAT':
            self.advance()
            node = NumNode(float(tok['value']), 'float')
            node.line = tok['line']
            node.column = tok['column']
            return node

        # Identifier: could be a variable reference OR a function call
        if tok['type'] == 'ID':
            self.advance()
            # Check for function call: name(args...)
            if self.current_token and self.current_token['type'] == 'LPAREN':
                return self._parse_func_call(tok)
            # Plain variable reference
            node = VarNode(tok['value'])
            node.line = tok['line']
            node.column = tok['column']
            return node

        # Parenthesized expression
        if tok['type'] == 'LPAREN':
            self.advance()
            node = self.expr()
            self.expect('RPAREN')
            return node

        self.error(f"Unexpected token {tok['type']} ('{tok['value']}') in expression")
        self.advance()
        raise SyntaxError("Unexpected token in expression")

    def _parse_func_call(self, name_tok) -> FuncCallNode:
        """
        Parses the argument list of a function call after the identifier has been consumed.
        name_tok is the already-consumed ID token.
        """
        self.expect('LPAREN')
        args = []
        while self.current_token and self.current_token['type'] != 'RPAREN':
            args.append(self.expr())
            if self.current_token and self.current_token['type'] == 'COMMA':
                self.advance()
        self.expect('RPAREN')
        node = FuncCallNode(name_tok['value'], args)
        node.line = name_tok['line']
        node.column = name_tok['column']
        return node
