class TargetCodeGenerator:
    """
    Target Code Generator.
    Converts Intermediate Three-Address Code (TAC) into accumulator-style pseudo-assembly.
    Supports limited function call/return target translation.
    """
    def __init__(self, tac_instructions: list):
        self.tac_instructions = tac_instructions
        self.assembly = []

    def generate(self) -> list:
        """Processes all TAC instructions and returns target pseudo-assembly statements."""
        for inst in self.tac_instructions:
            self.translate(inst)
        return self.assembly

    def translate(self, inst):
        op = inst.op
        arg1 = inst.arg1
        arg2 = inst.arg2
        result = inst.result

        # Comments to link TAC to Assembly in outputs
        self.assembly.append(f"; {str(inst)}")

        if op == 'ASSIGN':
            self.assembly.append(f"LOAD  {arg1}")
            self.assembly.append(f"STORE {result}")

        elif op in ('ADD', 'SUB', 'MUL', 'DIV'):
            # Load left operand, perform op on right operand, store in result
            self.assembly.append(f"LOAD  {arg1}")
            self.assembly.append(f"{op:<5} {arg2}")
            self.assembly.append(f"STORE {result}")

        elif op in ('EQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'):
            # Comparison operations: LOAD arg1, CMP operator arg2, STORE result
            symbol = {
                'EQ': '==', 'NEQ': '!=', 'LT': '<', 'GT': '>', 'LTE': '<=', 'GTE': '>='
            }.get(op, op)
            self.assembly.append(f"LOAD  {arg1}")
            self.assembly.append(f"CMP   {symbol} {arg2}")
            self.assembly.append(f"STORE {result}")

        elif op == 'UNARY_MINUS':
            # Unary minus compiled as subtraction from zero
            self.assembly.append(f"LOAD  0")
            self.assembly.append(f"SUB   {arg1}")
            self.assembly.append(f"STORE {result}")

        elif op == 'LABEL':
            # Label declaration: L0:
            self.assembly.append(f"{arg1}:")

        elif op == 'GOTO':
            # Unconditional jump
            self.assembly.append(f"JMP   {arg1}")

        elif op == 'IF_FALSE':
            # Load flag, branch if false
            self.assembly.append(f"LOAD  {arg1}")
            self.assembly.append(f"JMP_F {arg2}")

        elif op == 'FUNC_BEGIN':
            self.assembly.append(f"{arg1}:")
            self.assembly.append("PUSH  BP")
            self.assembly.append("MOV   BP, SP")

        elif op == 'FUNC_END':
            self.assembly.append("MOV   SP, BP")
            self.assembly.append("POP   BP")
            self.assembly.append("RET")

        elif op == 'PARAM':
            self.assembly.append(f"PUSH  {arg1}")

        elif op == 'CALL':
            self.assembly.append(f"CALL  {arg1}")
            self.assembly.append(f"ADD   SP, {arg2}")
            if result:
                self.assembly.append(f"STORE {result}")

        elif op == 'RETURN':
            if arg1 is not None:
                self.assembly.append(f"LOAD  {arg1}")
            self.assembly.append("MOV   SP, BP")
            self.assembly.append("POP   BP")
            self.assembly.append("RET")

        self.assembly.append("")  # Empty line separator for readability
