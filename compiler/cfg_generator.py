class CFGGenerator:
    """
    Control Flow Graph (CFG) Generator.
    Splits Three-Address Code (TAC) instructions into basic blocks
    and constructs the directed control flow graph.
    """
    def __init__(self, instructions: list):
        self.instructions = instructions

    def generate(self) -> dict:
        if not self.instructions:
            return {"nodes": [], "edges": []}

        # Step 1: Identify leaders
        leaders = {0}
        for i, inst in enumerate(self.instructions):
            # Instructions following jumps/returns/ends are leaders
            if inst.op in ('GOTO', 'IF_FALSE', 'RETURN', 'FUNC_END'):
                if i + 1 < len(self.instructions):
                    leaders.add(i + 1)
            # Labels and function entry points are leaders
            if inst.op in ('LABEL', 'FUNC_BEGIN'):
                leaders.add(i)

        sorted_leaders = sorted(list(leaders))
        
        # Step 2: Create basic blocks
        blocks = []
        for idx, start_idx in enumerate(sorted_leaders):
            end_idx = sorted_leaders[idx + 1] if idx + 1 < len(sorted_leaders) else len(self.instructions)
            block_insts = self.instructions[start_idx:end_idx]
            blocks.append({
                "id": f"B{idx}",
                "start": start_idx,
                "end": end_idx - 1,
                "instructions": block_insts
            })

        # Map label names and func names to their block IDs
        label_to_block = {}
        for b in blocks:
            for inst in b["instructions"]:
                if inst.op == 'LABEL':
                    label_to_block[inst.arg1] = b["id"]
                elif inst.op == 'FUNC_BEGIN':
                    label_to_block[inst.arg1] = b["id"]

        # Step 3: Construct edges
        edges = []
        for idx, b in enumerate(blocks):
            last_inst = b["instructions"][-1]
            op = last_inst.op

            if op == 'GOTO':
                target_label = last_inst.arg1
                if target_label in label_to_block:
                    edges.append({"from": b["id"], "to": label_to_block[target_label]})
            elif op == 'IF_FALSE':
                target_label = last_inst.arg2
                if target_label in label_to_block:
                    edges.append({"from": b["id"], "to": label_to_block[target_label]})
                # Fallthrough to the next block
                if idx + 1 < len(blocks):
                    edges.append({"from": b["id"], "to": blocks[idx + 1]["id"]})
            elif op in ('RETURN', 'FUNC_END'):
                # Jumps out of function scope; no direct fallthrough in local CFG
                pass
            else:
                # Normal fallthrough to the next block
                if idx + 1 < len(blocks):
                    # Make sure we don't fall through across separate functions
                    next_first_inst = blocks[idx + 1]["instructions"][0]
                    if next_first_inst.op != 'FUNC_BEGIN':
                        edges.append({"from": b["id"], "to": blocks[idx + 1]["id"]})

        # Step 4: Determine node types (entry/exit/normal) for styling
        nodes = []
        for idx, b in enumerate(blocks):
            label_text = "\\n".join([str(inst) for inst in b["instructions"]])
            
            # Determine node type
            if idx == 0:
                node_type = "entry"
            elif any(inst.op in ('RETURN', 'FUNC_END') for inst in b["instructions"]):
                node_type = "exit"
            else:
                node_type = "normal"

            nodes.append({
                "id": b["id"],
                "label": label_text,
                "type": node_type
            })

        return {"nodes": nodes, "edges": edges}
