# 🔧 Mini Compiler IDE

An educational, full-stack compiler visualization platform built in Python + Flask. It transforms C-like source code through every classical compiler stage — from lexical analysis all the way to pseudo-assembly target code — with an interactive web IDE powered by Monaco Editor and D3.js.

---

## 📸 Overview

The IDE provides a real-time, step-by-step view of every compiler phase:

```
Source Code → Lexical Analysis → Syntax Analysis → Semantic Analysis
           → IR (TAC) Generation → Optimization → Target Code Generation
```

Each phase is visualized in a dedicated tab: token listings, AST trees, symbol tables, error diagnostics, TAC code, an optimization log, pseudo-assembly output, and an interactive Control Flow Graph (CFG).

---

## 🚀 Features

### Compiler Phases
| Phase | Description |
|---|---|
| **Lexical Analysis** | Tokenizes C-like source code into a typed token stream with line/column tracking |
| **Syntax Analysis** | Recursive-descent parser builds an Abstract Syntax Tree (AST) with error recovery |
| **Semantic Analysis** | Validates scoping, duplicate declarations, undeclared variables, and type mismatches |
| **IR / TAC Generation** | Converts the AST into Three-Address Code (TAC) intermediate representation |
| **Code Optimization** | Applies Constant Folding, Constant Propagation, and Dead Code Elimination |
| **Target Code Generation** | Generates accumulator-style pseudo-assembly instructions |
| **CFG Visualization** | Splits TAC into basic blocks and renders a D3.js interactive Control Flow Graph |

### Language Support
The compiler handles a C-like language subset with:
- **Data types:** `int`, `float`
- **Declarations & Assignments:** `int x = 5;`, `y = x + 2;`
- **Control flow:** `if / else`, `while`, `for`
- **Functions:** `int/float/void` declarations with parameters, return statements, and function calls
- **Operators:** Arithmetic (`+`, `-`, `*`, `/`), Relational (`==`, `!=`, `<`, `>`, `<=`, `>=`), Unary negation
- **Comments:** Single-line (`//`) and block (`/* */`)

### IDE Features
- **Monaco Editor** — VS Code-grade editor with C syntax highlighting
- **8 Output Tabs** — Tokens, AST, Symbol Table, Errors, TAC, Optimized TAC, Assembly, CFG
- **Pipeline Visualizer** — Shows which compiler stage is active / succeeded / errored
- **Error Diagnostics** — Inline Monaco error markers + detailed error panel with line/column info
- **11 Sample Programs** — Pre-loaded examples covering every language feature
- **D3.js CFG** — Draggable, zoomable, force-directed control flow graph

---

## 🗂️ Project Structure

```
Compiler/
├── app.py                        # Flask application — routes & compiler pipeline orchestrator
├── requirements.txt              # Python dependencies
│
├── compiler/                     # Core compiler modules
│   ├── __init__.py
│   ├── lexer.py                  # Lexical Analyzer — regex-based tokenizer
│   ├── parser.py                 # Recursive-descent Parser → AST builder
│   ├── ast_nodes.py              # AST node class definitions
│   ├── semantic.py               # Semantic Analyzer — scoping & type checking
│   ├── codegen.py                # TAC Generator — AST → Three-Address Code
│   ├── optimizer.py              # TAC Optimizer — constant folding/propagation/DCE
│   ├── cfg_generator.py          # CFG Generator — basic blocks + directed edges
│   └── target_codegen.py         # Target Code Generator — pseudo-assembly output
│
├── templates/
│   └── index.html                # Main Jinja2 HTML template
│
├── static/
│   ├── css/
│   │   └── style.css             # Full dark-theme design system
│   └── js/
│       ├── main.js               # App logic — fetch, render, Monaco, D3 CFG
│       └── d3.min.js             # D3.js v7 (local, for CFG visualization)
│
├── sample_programs/              # Pre-loaded .c example programs
│   ├── arithmetic.c
│   ├── if_else.c
│   ├── while_loop.c
│   ├── for_loop.c
│   ├── nested_if.c
│   ├── nested_loop.c
│   ├── functions.c
│   ├── optimization_demo.c
│   ├── semantic_error.c
│   ├── type_mismatch.c
│   └── undeclared_variable.c
│
└── test_compiler.py              # Unit test suite (11 tests)
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python **3.9+**
- pip

### 1. Clone the repository
```bash
git clone <repository-url>
cd Compiler
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

`requirements.txt` contains:
```
flask
```

### 3. Run the development server
```bash
python app.py
```

The app starts on **http://127.0.0.1:5000** in debug mode.

---

## 🖥️ Usage

1. **Open** http://127.0.0.1:5000 in your browser.
2. **Write or load** a C-like program using the Monaco editor on the left, or pick one from the **"Load Sample"** dropdown.
3. **Click "Run Compiler"** to run the full compilation pipeline.
4. **Browse the output tabs** on the right:

| Tab | What you see |
|---|---|
| **Tokens** | Token type, lexeme, line, column for every token |
| **AST** | Nested tree view of the Abstract Syntax Tree |
| **Symbol Table** | Variable name, type, scope level, and declaration line |
| **Errors** | All lexical, syntax, and semantic errors with line info |
| **TAC** | Raw Three-Address Code instructions |
| **Optimized TAC** | Side-by-side pre/post-optimization TAC + optimization log |
| **Assembly** | Pseudo-assembly target code output |
| **CFG** | Interactive D3.js Control Flow Graph with drag & zoom |

---

## 🧪 Running Tests

```bash
python test_compiler.py
```

The test suite covers all 11 sample programs across all compiler phases:

```
...........
----------------------------------------------------------------------
Ran 11 tests in 0.004s

OK
```

---

## 🔬 Compiler Architecture

### Lexer (`lexer.py`)
Uses a combined regex master pattern (`re.compile`) with named groups. Tracks line and column numbers precisely, emitting `NEWLINE` tokens to advance the line counter. Supports all operators, keywords, identifiers, integer/float literals, and both comment styles.

### Parser (`parser.py`)
A hand-written **recursive-descent parser** that builds a typed AST. Features:
- Lookahead (`_peek_is_func_decl`) to distinguish function declarations from variable declarations
- Error recovery via a `synchronize()` method that skips to statement boundaries
- Full support for nested blocks, for/while/if-else, and function call expressions

### Semantic Analyzer (`semantic.py`)
Implements a **lexical scoping** system using a linked-list of `Scope` objects. Checks:
- Duplicate variable/function declarations
- Undeclared variable or function usage
- Float-to-int type mismatch on assignments and return values
- Return statement outside a function / wrong return type

### TAC Generator (`codegen.py`)
Visitor-pattern AST traversal emitting `TACInstruction` objects. Uses a monotonically-increasing `t0, t1, t2...` temporary counter and `L0, L1...` label counter. Supports all control flow structures and function call sequences (`PARAM` + `CALL`).

### Optimizer (`optimizer.py`)
Two-pass optimization on the TAC instruction list:
1. **Constant Folding** — evaluates compile-time constant expressions (e.g., `2 + 3` → `5`)
2. **Constant Propagation** — substitutes known constant values into later instructions
3. **Dead Code Elimination** — removes assignments to temporaries never read downstream

### CFG Generator (`cfg_generator.py`)
Identifies **basic block leaders** (first instruction, targets of jumps, instructions after jumps), partitions TAC into blocks, then constructs directed edges based on `GOTO`, `IF_FALSE`, and fallthrough semantics.

### Target Code Generator (`target_codegen.py`)
Generates accumulator-style pseudo-assembly using `LOAD`, `STORE`, `ADD`, `SUB`, `MUL`, `DIV`, `CMP`, `JMP*`, and `CALL`/`RET` instructions.

---

## 📋 Sample Programs

| File | Demonstrates |
|---|---|
| `arithmetic.c` | Basic expressions: `(a + b) * 2 - 4 / 2` |
| `if_else.c` | Conditional branching with `if / else` |
| `while_loop.c` | While loop with accumulator |
| `for_loop.c` | C-style `for` loop with local variable |
| `nested_if.c` | Multi-level nested conditionals |
| `nested_loop.c` | Nested `for` loops |
| `functions.c` | Function declaration + call (`square(a)`) |
| `optimization_demo.c` | Constant folding & propagation showcase |
| `semantic_error.c` | Duplicate variable declaration (expected error) |
| `type_mismatch.c` | Float assigned to int (expected error) |
| `undeclared_variable.c` | Usage before declaration (expected error) |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3, Flask |
| Frontend | HTML5, Vanilla CSS, JavaScript (ES2020) |
| Code Editor | Monaco Editor v0.44 (CDN) |
| Graph Visualization | D3.js v7 (local) |
| Icon Library | Font Awesome 6.4 |
| Fonts | Google Fonts — Inter, Outfit, Fira Code |

---

## 👤 Author

**Mannan Rishi**  
Mini Compiler
© 2026. All rights reserved.
