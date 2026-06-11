from compiler.codegen import TACInstruction

def is_literal(val) -> bool:
    """Helper to check if a TAC operand is a literal numeric constant."""
    if val is None:
        return False
    val_str = str(val)
    # Check positive numbers and decimals
    if val_str.replace('.', '', 1).isdigit():
        return True
    # Check negative numbers
    if val_str.startswith('-') and val_str[1:].replace('.', '', 1).isdigit():
        return True
    return False


class TACOptimizer:
    """
    Three-Address Code (TAC) Optimizer.
    Applies Constant Folding, Constant Propagation, and Dead Code Elimination.
    """
    def __init__(self, instructions: list):
        self.instructions = instructions
        self.logs = []  # Log messages explaining each optimization step

    def optimize(self) -> list:
        """Runs optimization passes iteratively until no more instructions can be optimized."""
        current_instrs = self.instructions
        for i in range(5):  # Set an upper limit of 5 iterations
            changed = False

            # Pass 1: Constant Propagation & Folding
            opt_instrs, prop_changed = self.pass_constant_propagation_and_folding(current_instrs)
            if prop_changed:
                changed = True
                current_instrs = opt_instrs

            # Pass 2: Dead Code Elimination
            opt_instrs, dce_changed = self.pass_dead_code_elimination(current_instrs)
            if dce_changed:
                changed = True
                current_instrs = opt_instrs

            if not changed:
                break

        return current_instrs

    def pass_constant_propagation_and_folding(self, instrs: list) -> tuple:
        """Performs basic-block-level constant propagation and algebraic folding."""
        optimized = []
        constants = {}  # Tracks constant values for variables in the current block
        changed = False

        for inst in instrs:
            # Safe Approximation: clear constant mappings at control flow labels, jumps,
            # or function boundaries to prevent incorrect propagation.
            if inst.op in ('LABEL', 'GOTO', 'IF_FALSE', 'FUNC_BEGIN', 'FUNC_END', 'CALL', 'RETURN'):
                constants.clear()

            # Create a copy of the instruction operands for modification
            op = inst.op
            arg1 = inst.arg1
            arg2 = inst.arg2
            result = inst.result

            # 1. Propagate constants
            if arg1 in constants:
                arg1 = constants[arg1]
                changed = True
            if arg2 in constants:
                arg2 = constants[arg2]
                changed = True

            # 2. Fold operations
            folded = False
            folded_val = None

            if op in ('ADD', 'SUB', 'MUL', 'DIV', 'EQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'):
                if is_literal(arg1) and is_literal(arg2):
                    # Convert operands to float or int
                    v1 = float(arg1) if '.' in str(arg1) else int(arg1)
                    v2 = float(arg2) if '.' in str(arg2) else int(arg2)

                    try:
                        if op == 'ADD':
                            folded_val = v1 + v2
                        elif op == 'SUB':
                            folded_val = v1 - v2
                        elif op == 'MUL':
                            folded_val = v1 * v2
                        elif op == 'DIV':
                            folded_val = v1 / v2 if v2 != 0 else 0
                        elif op == 'EQ':
                            folded_val = 1 if v1 == v2 else 0
                        elif op == 'NEQ':
                            folded_val = 1 if v1 != v2 else 0
                        elif op == 'LT':
                            folded_val = 1 if v1 < v2 else 0
                        elif op == 'GT':
                            folded_val = 1 if v1 > v2 else 0
                        elif op == 'LTE':
                            folded_val = 1 if v1 <= v2 else 0
                        elif op == 'GTE':
                            folded_val = 1 if v1 >= v2 else 0

                        # Convert folded value back to representation
                        folded_val = str(folded_val)
                        op = 'ASSIGN'
                        arg1 = folded_val
                        arg2 = None
                        folded = True
                        changed = True
                        self.logs.append(f"Folded expression: {inst.arg1} {inst.op} {inst.arg2} -> {folded_val}")
                    except ZeroDivisionError:
                        pass # Ignore compile-time division by zero errors; let them raise at runtime

            elif op == 'UNARY_MINUS' and is_literal(arg1):
                v1 = float(arg1) if '.' in str(arg1) else int(arg1)
                folded_val = str(-v1)
                op = 'ASSIGN'
                arg1 = folded_val
                folded = True
                changed = True
                self.logs.append(f"Folded unary negation: -({inst.arg1}) -> {folded_val}")

            # 3. Update active constants map for subsequent propagation
            if op == 'ASSIGN':
                if is_literal(arg1):
                    # Propagation mapping
                    constants[result] = arg1
                    # If this assignment is propagating a new constant, log it (unless it was already logged)
                    if inst.arg1 != arg1:
                        self.logs.append(f"Propagated constant '{arg1}' into variable '{result}'")
                else:
                    # If assigned a non-constant, remove it from mapping
                    if result in constants:
                        constants.pop(result)

            # 4. Handle conditional jump simplification
            skip_instruction = False
            if op == 'IF_FALSE':
                if is_literal(arg1):
                    v_cond = float(arg1) if '.' in str(arg1) else int(arg1)
                    if v_cond == 0:
                        # jump condition is FALSE; jump is ALWAYS taken
                        op = 'GOTO'
                        arg1 = arg2  # destination label
                        arg2 = None
                        changed = True
                        self.logs.append(f"Simplified conditional branch 'ifFalse 0' into unconditional 'goto {arg1}'")
                    else:
                        # jump condition is TRUE; jump is NEVER taken, skip instruction
                        skip_instruction = True
                        changed = True
                        self.logs.append(f"Removed unreachable conditional branch branch 'ifFalse {arg1}'")

            if not skip_instruction:
                optimized.append(TACInstruction(op, arg1, arg2, result))

        return optimized, changed

    def pass_dead_code_elimination(self, instrs: list) -> tuple:
        """Removes assignments/instructions writing to temporary variables that are never read."""
        optimized = []
        used_vars = set()
        changed = False

        # Helper to check if variable name is a compiler temporary (e.g. t0, t1)
        def is_temp(var_name) -> bool:
            if not var_name:
                return False
            var_str = str(var_name)
            return var_str.startswith('t') and var_str[1:].isdigit()

        # Step 1: Scan all instructions to build a set of read variables
        for inst in instrs:
            if inst.op == 'IF_FALSE':
                used_vars.add(inst.arg1)
            elif inst.op in ('ASSIGN', 'PARAM', 'RETURN'):
                if inst.arg1 and not is_literal(inst.arg1):
                    used_vars.add(inst.arg1)
            elif inst.op in ('ADD', 'SUB', 'MUL', 'DIV', 'EQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'):
                if inst.arg1 and not is_literal(inst.arg1):
                    used_vars.add(inst.arg1)
                if inst.arg2 and not is_literal(inst.arg2):
                    used_vars.add(inst.arg2)
            elif inst.op == 'UNARY_MINUS':
                if inst.arg1 and not is_literal(inst.arg1):
                    used_vars.add(inst.arg1)

        # Step 2: Filter out dead assignments to compiler temporaries only
        for inst in instrs:
            if inst.result:
                # Dead code elimination applies ONLY to compiler-generated temporaries (like t0, t1)
                # If a temporary variable is written to but never read downstream, it's dead.
                if is_temp(inst.result) and inst.result not in used_vars:
                    self.logs.append(f"Removed dead code: temporary assignment to '{inst.result}' is never read")
                    changed = True
                    continue
            optimized.append(inst)

        return optimized, changed
