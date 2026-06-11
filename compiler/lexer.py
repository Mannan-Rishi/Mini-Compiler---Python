import re

class Lexer:
    """
    Lexical Analyzer for the Mini Compiler.
    Tokenizes input source code into a stream of tokens, tracking lines, columns,
    and capturing lexical errors.
    """
    def __init__(self, code: str):
        self.code = code
        self.tokens = []
        self.errors = []
        self.tokenize()

    def tokenize(self):
        token_rules = [
            ('COMMENT_BLOCK',  r'/\*[\s\S]*?\*/'),         # Block comments /* ... */
            ('COMMENT_LINE',   r'//[^\n]*'),               # Single line comments // ...
            ('FLOAT',          r'\d+\.\d+'),               # Float literals (e.g. 3.14)
            ('INT',            r'\d+'),                    # Integer literals (e.g. 42)
            # Keywords — includes void and return for function support
            ('KEYWORD',        r'\b(int|float|void|if|else|while|for|return)\b'),
            ('ID',             r'[a-zA-Z_][a-zA-Z0-9_]*'), # Identifiers (variables)
            ('EQ',             r'=='),                     # Comparison Equals
            ('NEQ',            r'!='),                     # Comparison Not Equals
            ('LTE',            r'<='),                     # Comparison Less-than or Equal
            ('GTE',            r'>='),                     # Comparison Greater-than or Equal
            ('LT',             r'<'),                      # Comparison Less-than
            ('GT',             r'>'),                      # Comparison Greater-than
            ('ASSIGN',         r'='),                      # Assignment operator
            ('PLUS',           r'\+'),                     # Operator Add
            ('MINUS',          r'-'),                      # Operator Subtract
            ('MUL',            r'\*'),                     # Operator Multiply
            ('DIV',            r'/'),                      # Operator Divide
            ('LPAREN',         r'\('),                     # Left Parenthesis
            ('RPAREN',         r'\)'),                     # Right Parenthesis
            ('LBRACE',         r'\{'),                     # Left Curly Brace
            ('RBRACE',         r'\}'),                     # Right Curly Brace
            ('SEMI',           r';'),                      # Semicolon delimiter
            ('COMMA',          r','),                      # Comma delimiter
            ('NEWLINE',        r'\n'),                     # Newline (increment line count)
            ('SKIP',           r'[ \t\r]+'),               # Whitespace to skip
            ('MISMATCH',       r'.'),                      # Any invalid character
        ]

        # Combine all regex rules into a named-group master regex
        regex_parts = [f'(?P<{name}>{pattern})' for name, pattern in token_rules]
        master_regex = re.compile('|'.join(regex_parts))

        line_num = 1
        line_start = 0

        for match in master_regex.finditer(self.code):
            kind = match.lastgroup
            value = match.group(kind)
            column = match.start() - line_start + 1

            if kind == 'NEWLINE':
                line_num += 1
                line_start = match.end()
            elif kind == 'SKIP':
                pass
            elif kind == 'COMMENT_LINE':
                # Inline comments don't consume the newline, so line/column stays correct
                pass
            elif kind == 'COMMENT_BLOCK':
                # Block comments can span multiple lines
                newlines = value.count('\n')
                if newlines > 0:
                    line_num += newlines
                    line_start = match.start() + value.rfind('\n') + 1
            elif kind == 'MISMATCH':
                self.errors.append({
                    "message": f"Unexpected character '{value}'",
                    "line": line_num,
                    "column": column
                })
            else:
                self.tokens.append({
                    "type": kind,
                    "value": value,
                    "line": line_num,
                    "column": column
                })

    def get_tokens(self):
        return self.tokens

    def get_errors(self):
        return self.errors
