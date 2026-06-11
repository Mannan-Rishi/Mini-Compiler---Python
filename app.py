import os
from flask import Flask, render_template, jsonify, request
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import SemanticAnalyzer
from compiler.codegen import TACGenerator
from compiler.optimizer import TACOptimizer
from compiler.target_codegen import TargetCodeGenerator
from compiler.cfg_generator import CFGGenerator

app = Flask(__name__)

# Base directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, 'sample_programs')

@app.route('/')
def index():
    """Serves the main Web IDE homepage."""
    return render_template('index.html')

@app.route('/samples', methods=['GET'])
def get_samples():
    """Dynamically reads and returns the list of pre-loaded sample program contents."""
    samples = {}
    if os.path.exists(SAMPLE_DIR):
        for filename in os.listdir(SAMPLE_DIR):
            if filename.endswith('.c'):
                name = os.path.splitext(filename)[0]
                filepath = os.path.join(SAMPLE_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        samples[name] = f.read()
                except Exception as e:
                    samples[name] = f"// Error reading sample: {str(e)}"
    return jsonify(samples)

@app.route('/compile', methods=['POST'])
def compile_code():
    """Runs the full compiler pipeline on the input source code."""
    data = request.get_json() or {}
    code = data.get('code', '')

    # Initialize results payload
    result_payload = {
        "tokens": [],
        "lexical_errors": [],
        "ast": None,
        "syntax_errors": [],
        "semantic_errors": [],
        "symbol_table": [],
        "tac": [],
        "optimized_tac": [],
        "optimization_logs": [],
        "target_code": [],
        "cfg": {"nodes": [], "edges": []},
        "success": False
    }

    try:
        # Phase 1: Lexical Analysis
        lexer = Lexer(code)
        tokens = lexer.get_tokens()
        lex_errors = lexer.get_errors()
        
        result_payload["tokens"] = tokens
        result_payload["lexical_errors"] = lex_errors

        # Phase 2: Syntax Analysis
        parser = Parser(tokens)
        ast_root = None
        try:
            ast_root = parser.parse()
        except Exception:
            pass
        
        result_payload["syntax_errors"] = parser.errors
        if ast_root:
            result_payload["ast"] = ast_root.to_dict()

        # Stop compilation if there are lexical or syntactic errors
        if lex_errors or parser.errors:
            result_payload["success"] = False
            return jsonify(result_payload)

        if not ast_root:
            result_payload["success"] = False
            result_payload["syntax_errors"].append({
                "message": "Parser failed to construct an Abstract Syntax Tree.",
                "line": 1,
                "column": 1
            })
            return jsonify(result_payload)

        # Phase 3: Semantic Analysis & Symbol Table
        semantic_analyzer = SemanticAnalyzer()
        semantic_errors, symbol_table = semantic_analyzer.analyze(ast_root)
        
        result_payload["semantic_errors"] = semantic_errors
        result_payload["symbol_table"] = symbol_table

        if semantic_errors:
            result_payload["success"] = False
            return jsonify(result_payload)

        # Phase 4: Intermediate Code Generation (TAC)
        tac_generator = TACGenerator()
        tac_instructions = tac_generator.generate(ast_root)
        
        # Store pre-optimized TAC as strings
        result_payload["tac"] = [str(inst) for inst in tac_instructions]

        # Phase 5: Code Optimization
        optimizer = TACOptimizer(tac_instructions)
        optimized_instructions = optimizer.optimize()
        
        result_payload["optimized_tac"] = [str(inst) for inst in optimized_instructions]
        result_payload["optimization_logs"] = optimizer.logs

        # Phase 5.5: Control Flow Graph (CFG) Generation
        cfg_gen = CFGGenerator(optimized_instructions)
        result_payload["cfg"] = cfg_gen.generate()

        # Phase 6: Target Code Generation (Pseudo-Assembly)
        target_generator = TargetCodeGenerator(optimized_instructions)
        assembly_instructions = target_generator.generate()
        
        result_payload["target_code"] = assembly_instructions
        result_payload["success"] = True

    except Exception as e:
        # Global crash protection: report it as a syntax/system error
        import traceback
        result_payload["success"] = False
        result_payload["syntax_errors"].append({
            "message": f"Compiler pipeline crash: {str(e)}\n{traceback.format_exc()}",
            "line": 1,
            "column": 1
        })

    return jsonify(result_payload)

if __name__ == '__main__':
    # Start the local development server
    app.run(debug=True, host='127.0.0.1', port=5000)
