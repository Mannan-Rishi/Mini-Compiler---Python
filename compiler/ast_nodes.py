class ASTNode:
    """Base class for all Abstract Syntax Tree nodes."""
    def to_dict(self) -> dict:
        raise NotImplementedError("Subclasses must implement to_dict()")


class ProgramNode(ASTNode):
    """Represents the root program node containing a list of statements."""
    def __init__(self, statements):
        self.statements = statements

    def to_dict(self) -> dict:
        return {
            "type": "Program",
            "children": [stmt.to_dict() for stmt in self.statements]
        }


class VarDeclNode(ASTNode):
    """Represents a variable declaration (e.g., 'int x = 5;' or 'float y;')."""
    def __init__(self, type_name: str, var_name: str, init_expr: ASTNode = None):
        self.type_name = type_name
        self.var_name = var_name
        self.init_expr = init_expr

    def to_dict(self) -> dict:
        data = {
            "type": "VarDecl",
            "var_name": self.var_name,
            "type_name": self.type_name,
            "children": []
        }
        if self.init_expr:
            data["children"].append(self.init_expr.to_dict())
        return data


class AssignNode(ASTNode):
    """Represents a variable assignment (e.g., 'x = y + 2;')."""
    def __init__(self, var_name: str, expr: ASTNode):
        self.var_name = var_name
        self.expr = expr

    def to_dict(self) -> dict:
        return {
            "type": "Assignment",
            "var_name": self.var_name,
            "children": [self.expr.to_dict()]
        }


class IfNode(ASTNode):
    """Represents an if-else condition."""
    def __init__(self, condition: ASTNode, then_block: ASTNode, else_block: ASTNode = None):
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

    def to_dict(self) -> dict:
        children = [
            {"type": "Condition", "children": [self.condition.to_dict()]},
            {"type": "Then", "children": [self.then_block.to_dict()]}
        ]
        if self.else_block:
            children.append({"type": "Else", "children": [self.else_block.to_dict()]})
        
        return {
            "type": "IfStatement",
            "children": children
        }


class WhileNode(ASTNode):
    """Represents a while loop."""
    def __init__(self, condition: ASTNode, body: ASTNode):
        self.condition = condition
        self.body = body

    def to_dict(self) -> dict:
        return {
            "type": "WhileLoop",
            "children": [
                {"type": "Condition", "children": [self.condition.to_dict()]},
                {"type": "Body", "children": [self.body.to_dict()]}
            ]
        }


class ForNode(ASTNode):
    """Represents a for loop (e.g., 'for (int i = 0; i < 10; i = i + 1) { ... }')."""
    def __init__(self, init_stmt: ASTNode, condition: ASTNode, update_stmt: ASTNode, body: ASTNode):
        self.init_stmt = init_stmt
        self.condition = condition
        self.update_stmt = update_stmt
        self.body = body

    def to_dict(self) -> dict:
        children = []
        if self.init_stmt:
            children.append({"type": "Init", "children": [self.init_stmt.to_dict()]})
        if self.condition:
            children.append({"type": "Condition", "children": [self.condition.to_dict()]})
        if self.update_stmt:
            children.append({"type": "Update", "children": [self.update_stmt.to_dict()]})
        children.append({"type": "Body", "children": [self.body.to_dict()]})

        return {
            "type": "ForLoop",
            "children": children
        }


class BlockNode(ASTNode):
    """Represents a scope block delimited by curly braces (e.g., '{ stmt1; stmt2; }')."""
    def __init__(self, statements):
        self.statements = statements

    def to_dict(self) -> dict:
        return {
            "type": "Block",
            "children": [stmt.to_dict() for stmt in self.statements]
        }


class BinOpNode(ASTNode):
    """Represents a binary operation (+, -, *, /, ==, !=, <, >, <=, >=)."""
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op
        self.right = right

    def to_dict(self) -> dict:
        return {
            "type": "BinOp",
            "op": self.op,
            "children": [self.left.to_dict(), self.right.to_dict()]
        }


class UnaryOpNode(ASTNode):
    """Represents a unary operation (e.g., -x)."""
    def __init__(self, op: str, expr: ASTNode):
        self.op = op
        self.expr = expr

    def to_dict(self) -> dict:
        return {
            "type": "UnaryOp",
            "op": self.op,
            "children": [self.expr.to_dict()]
        }


class NumNode(ASTNode):
    """Represents an integer or floating-point number literal."""
    def __init__(self, value, type_name: str):
        self.value = value
        self.type_name = type_name  # 'int' or 'float'

    def to_dict(self) -> dict:
        return {
            "type": f"Literal ({self.type_name})",
            "value": str(self.value)
        }


class VarNode(ASTNode):
    """Represents a variable reference (identifier)."""
    def __init__(self, name: str):
        self.name = name

    def to_dict(self) -> dict:
        return {
            "type": "Variable",
            "value": self.name
        }


# -------------------------------------------------------------------------
# Function-support nodes (limited: no recursion, no overloading)
# -------------------------------------------------------------------------

class ParamNode(ASTNode):
    """Represents a single function parameter declaration (e.g., 'int a')."""
    def __init__(self, type_name: str, var_name: str):
        self.type_name = type_name
        self.var_name = var_name

    def to_dict(self) -> dict:
        return {
            "type": "Param",
            "type_name": self.type_name,
            "var_name": self.var_name,
            "children": []
        }


class FuncDeclNode(ASTNode):
    """Represents a function declaration (e.g., 'int add(int a, int b) { return a + b; }')."""
    def __init__(self, return_type: str, name: str, params: list, body: ASTNode):
        self.return_type = return_type  # 'int', 'float', or 'void'
        self.name = name
        self.params = params            # list of ParamNode
        self.body = body                # BlockNode

    def to_dict(self) -> dict:
        return {
            "type": "FuncDecl",
            "var_name": self.name,
            "type_name": self.return_type,
            "children": [p.to_dict() for p in self.params] + [self.body.to_dict()]
        }


class ReturnNode(ASTNode):
    """Represents a return statement (e.g., 'return x + 1;')."""
    def __init__(self, expr: ASTNode = None):
        self.expr = expr  # None for void returns

    def to_dict(self) -> dict:
        children = [self.expr.to_dict()] if self.expr else []
        return {
            "type": "Return",
            "children": children
        }


class FuncCallNode(ASTNode):
    """Represents a function call expression (e.g., 'add(a, b)')."""
    def __init__(self, name: str, args: list):
        self.name = name    # function name
        self.args = args    # list of ASTNode (expressions)

    def to_dict(self) -> dict:
        return {
            "type": "FuncCall",
            "var_name": self.name,
            "children": [a.to_dict() for a in self.args]
        }
