/* ==========================================================================
   MINI COMPILER IDE JS - CORE LOGIC WITH MONACO & D3.JS CFG
   ========================================================================== */

let editor; // Global Monaco Editor reference
let cachedSamples = {}; // Cache of loaded sample programs

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Monaco Editor using AMD loader
    require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs' } });
    
    require(['vs/editor/editor.main'], function() {
        editor = monaco.editor.create(document.getElementById('monaco-container'), {
            value: `// Academic C-like program showing nested loop and function calls
int square(int n) {
    return n * n;
}

int main() {
    int sum = 0;
    for (int i = 1; i <= 5; i = i + 1) {
        sum = sum + square(i);
    }
}`,
            language: 'c',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 14,
            lineHeight: 20,
            fontFamily: "'Fira Code', monospace"
        });

        // Initialize remainder of app functions once Editor is ready
        initApp();
    });
});

function initApp() {
    // DOM Elements
    const sampleSelect = document.getElementById('sample-select');
    const compileBtn = document.getElementById('compile-btn');
    const statusIndicator = document.getElementById('status-indicator');
    
    // Tab Elements
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    // Output DOM Nodes
    const tokensTable = document.getElementById('tokens-table').querySelector('tbody');
    const astContainer = document.getElementById('ast-container');
    const symbolTableBody = document.getElementById('symbol-table-data').querySelector('tbody');
    const compSuccessMsg = document.getElementById('compilation-success-message');
    const compErrorMsg = document.getElementById('compilation-error-message');
    const errorList = document.getElementById('error-list');
    const tacCode = document.getElementById('tac-code');
    const preOptTacCode = document.getElementById('pre-opt-tac-code');
    const postOptTacCode = document.getElementById('post-opt-tac-code');
    const optLogsList = document.getElementById('opt-logs-list');
    const targetCodeBlock = document.getElementById('target-code-block');
    
    // Pipeline Steps
    const pipelineSteps = {
        source: document.getElementById('step-source'),
        lexer: document.getElementById('step-lexer'),
        parser: document.getElementById('step-parser'),
        semantic: document.getElementById('step-semantic'),
        codegen: document.getElementById('step-codegen'),
        optimizer: document.getElementById('step-optimizer'),
        target: document.getElementById('step-target')
    };

    // Tab Navigation Logic
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // Load Pre-loaded samples from Flask
    async function loadSamples() {
        try {
            const response = await fetch('/samples');
            cachedSamples = await response.json();
            
            for (const name in cachedSamples) {
                const option = document.createElement('option');
                option.value = name;
                // Beautify names for display (e.g. arithmetic -> Arithmetic Expression)
                const formattedName = name.split('_')
                                          .map(w => w.charAt(0).toUpperCase() + w.slice(1))
                                          .join(' ');
                option.textContent = formattedName;
                sampleSelect.appendChild(option);
            }

            // Default auto-select loaded sample matching initial editor code
            if (cachedSamples['functions']) {
                sampleSelect.value = 'functions';
                editor.setValue(cachedSamples['functions']);
            }
        } catch (e) {
            console.error("Failed to load sample templates", e);
        }
    }

    sampleSelect.addEventListener('change', () => {
        const selected = sampleSelect.value;
        if (selected && cachedSamples[selected]) {
            editor.setValue(cachedSamples[selected]);
            resetPipelineVisual();
        }
    });

    // Reset pipeline visualization styles
    function resetPipelineVisual() {
        for (const key in pipelineSteps) {
            pipelineSteps[key].className = 'pipeline-step';
        }
        pipelineSteps.source.classList.add('active');
        statusIndicator.className = 'status-badge status-idle';
        statusIndicator.textContent = 'IDLE';
        
        // Clear editor markers
        if (editor) {
            monaco.editor.setModelMarkers(editor.getModel(), "compiler", []);
        }
    }

    // Set pipeline visualization styles based on progress
    function updatePipelineVisual(stage, status) {
        for (const key in pipelineSteps) {
            pipelineSteps[key].className = 'pipeline-step';
        }

        const stages = ['source', 'lexer', 'parser', 'semantic', 'codegen', 'optimizer', 'target'];
        const currentIdx = stages.indexOf(stage);

        if (status === 'success') {
            for (let i = 0; i <= currentIdx; i++) {
                pipelineSteps[stages[i]].classList.add('success');
            }
            if (currentIdx < stages.length - 1) {
                pipelineSteps[stages[currentIdx + 1]].classList.add('active');
            }
        } else if (status === 'error') {
            for (let i = 0; i < currentIdx; i++) {
                pipelineSteps[stages[i]].classList.add('success');
            }
            pipelineSteps[stages[currentIdx]].classList.add('error');
        }
    }

    // Recursive function to build and render AST HTML list
    function createASTHTML(node) {
        if (!node) return null;
        
        const li = document.createElement('li');
        const nodeDiv = document.createElement('div');
        nodeDiv.className = 'ast-node';

        const typeSpan = document.createElement('span');
        typeSpan.className = 'ast-node-type';
        typeSpan.textContent = node.type || 'Node';
        nodeDiv.appendChild(typeSpan);

        if (node.var_name) {
            const valSpan = document.createElement('span');
            valSpan.className = 'ast-node-val';
            const typeInfo = node.type_name ? ` : ${node.type_name}` : '';
            valSpan.textContent = `'${node.var_name}'${typeInfo}`;
            nodeDiv.appendChild(valSpan);
        } else if (node.value !== undefined) {
            const valSpan = document.createElement('span');
            valSpan.className = 'ast-node-val';
            valSpan.textContent = `${node.value}`;
            nodeDiv.appendChild(valSpan);
        } else if (node.op) {
            const valSpan = document.createElement('span');
            valSpan.className = 'ast-node-val';
            valSpan.textContent = `[${node.op}]`;
            nodeDiv.appendChild(valSpan);
        }

        li.appendChild(nodeDiv);

        if (node.children && node.children.length > 0) {
            const ul = document.createElement('ul');
            node.children.forEach(child => {
                const childLi = createASTHTML(child);
                if (childLi) ul.appendChild(childLi);
            });
            li.appendChild(ul);
        }
        return li;
    }

    // Render AST Root
    function renderAST(astData) {
        astContainer.innerHTML = '';
        if (!astData) {
            astContainer.innerHTML = '<div class="text-center text-muted pad-20">No AST generated.</div>';
            return;
        }
        
        const ulRoot = document.createElement('ul');
        ulRoot.className = 'ast-tree';
        const rootLi = createASTHTML(astData);
        if (rootLi) {
            ulRoot.appendChild(rootLi);
            astContainer.appendChild(ulRoot);
        } else {
            astContainer.innerHTML = '<div class="text-center text-muted pad-20">Empty AST.</div>';
        }
    }

    // Switch tab to a specific target tab pane
    function switchToTab(tabId) {
        tabButtons.forEach(btn => {
            if (btn.getAttribute('data-tab') === tabId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        tabPanes.forEach(pane => {
            if (pane.id === tabId) {
                pane.classList.add('active');
            } else {
                pane.classList.remove('active');
            }
        });
    }

    // Helper to render compiler errors and highlight corresponding stage
    function showCompilationErrors(errors, stage) {
        statusIndicator.className = 'status-badge status-error';
        statusIndicator.textContent = 'ERROR';
        updatePipelineVisual(stage, 'error');

        // Hide success message, show error cards
        compSuccessMsg.style.display = 'none';
        compErrorMsg.style.display = 'block';

        errorList.innerHTML = '';
        errors.forEach(err => {
            const div = document.createElement('div');
            div.className = 'error-item';
            
            const locText = err.column !== undefined ? `Line ${err.line}, Col ${err.column}` : `Line ${err.line}`;
            
            div.innerHTML = `
                <span class="error-item-loc">${locText}</span>
                <span class="error-item-msg">${err.message}</span>
            `;
            errorList.appendChild(div);
        });

        // Set Editor error highlights (Monaco markers)
        if (editor) {
            const markers = errors.map(err => ({
                startLineNumber: err.line || 1,
                startColumn: err.column || 1,
                endLineNumber: err.line || 1,
                endColumn: err.column !== undefined ? err.column + 5 : 50,
                message: err.message,
                severity: monaco.MarkerSeverity.Error
            }));
            monaco.editor.setModelMarkers(editor.getModel(), "compiler", markers);
        }

        // Automatically switch to the diagnostics (Errors) tab
        switchToTab('tab-errors');
    }

    // D3.js Basic Blocks Control Flow Graph (CFG) Visualizer
    function renderCFG(cfgData) {
        // Remap edges from backend format {from, to} to D3 format {source, target}
        if (cfgData && cfgData.edges) {
            cfgData = {
                nodes: cfgData.nodes,
                edges: cfgData.edges.map(e => ({ source: e.from, target: e.to }))
            };
        }
        const container = document.getElementById('cfg-container');
        container.innerHTML = '';
        if (!cfgData || !cfgData.nodes || cfgData.nodes.length === 0) {
            container.innerHTML = '<div class="text-center text-muted pad-20">No CFG generated.</div>';
            return;
        }

        const width = container.clientWidth || 600;
        const height = 450;
        
        const svg = d3.select("#cfg-container").append("svg")
            .attr("width", "100%")
            .attr("height", height)
            .attr("viewBox", `0 0 ${width} ${height}`);
            
        const svgGroup = svg.append("g");
        
        // Add Zoom/Pan behaviors
        svg.call(d3.zoom().on("zoom", function (e) {
            svgGroup.attr("transform", e.transform);
        }));

        // Define Arrow Marker definitions
        svg.append("defs").append("marker")
            .attr("id", "arrow")
            .attr("viewBox", "0 0 10 10")
            .attr("refX", 18)
            .attr("refY", 5)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto-start-reverse")
            .append("path")
            .attr("d", "M 0 0 L 10 5 L 0 10 z")
            .attr("fill", "#9ca3af");

        // Link Edges path lines
        const link = svgGroup.selectAll(".cfg-edge")
            .data(cfgData.edges)
            .enter()
            .append("g")
            .attr("class", "cfg-edge");
            
        link.append("path")
            .attr("marker-end", "url(#arrow)")
            .attr("stroke", "#4b5563")
            .attr("stroke-width", "2px")
            .attr("fill", "none");

        // Nodes G elements
        const nodeGroup = svgGroup.selectAll(".cfg-node")
            .data(cfgData.nodes)
            .enter()
            .append("g")
            .attr("class", d => `cfg-node ${d.type}`);

        // Node Rect boxes
        nodeGroup.append("rect")
            .attr("width", 200)
            .attr("height", d => {
                const lines = d.label.split("\\n");
                return 35 + lines.length * 16;
            })
            .attr("x", -100)
            .attr("y", d => {
                const lines = d.label.split("\\n");
                return -(35 + lines.length * 16) / 2;
            });

        // Node Title text
        nodeGroup.append("text")
            .attr("class", "node-title")
            .attr("text-anchor", "middle")
            .attr("y", d => {
                const lines = d.label.split("\\n");
                return -(35 + lines.length * 16) / 2 + 18;
            })
            .text(d => d.id.toUpperCase());

        // Node Body instruction lines (tspan)
        nodeGroup.each(function(d) {
            const lines = d.label.split("\\n");
            const textElement = d3.select(this).append("text")
                .attr("text-anchor", "middle")
                .attr("y", -(35 + lines.length * 16) / 2 + 34);
                
            lines.forEach((line, i) => {
                textElement.append("tspan")
                    .attr("x", 0)
                    .attr("dy", i === 0 ? 0 : 16)
                    .text(line || " ");
            });
        });

        // Initialize Force Layout simulation
        const simulation = d3.forceSimulation(cfgData.nodes)
            .force("link", d3.forceLink(cfgData.edges).id(d => d.id).distance(140))
            .force("charge", d3.forceManyBody().strength(-350))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(110));

        simulation.on("tick", () => {
            link.select("path").attr("d", d => {
                const sx = d.source.x;
                const sy = d.source.y;
                const tx = d.target.x;
                const ty = d.target.y;
                return `M ${sx} ${sy} L ${tx} ${ty}`;
            });
            nodeGroup.attr("transform", d => `translate(${d.x}, ${d.y})`);
        });

        // Drag handlers
        nodeGroup.call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    }

    // Main Compilation Trigger
    compileBtn.addEventListener('click', async () => {
        const code = editor ? editor.getValue() : '';
        statusIndicator.className = 'status-badge status-running';
        statusIndicator.textContent = 'RUNNING';
        
        // Clear previous editor markers
        if (editor) {
            monaco.editor.setModelMarkers(editor.getModel(), "compiler", []);
        }

        try {
            const response = await fetch('/compile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });
            const result = await response.json();

            // 1. Process Lexical Analysis (Tokens)
            tokensTable.innerHTML = '';
            if (result.tokens && result.tokens.length > 0) {
                result.tokens.forEach((tok, index) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td><span class="type-badge">${tok.type}</span></td>
                        <td class="font-mono">${tok.value}</td>
                        <td>${tok.line}</td>
                        <td>${tok.column}</td>
                    `;
                    tokensTable.appendChild(row);
                });
            } else {
                tokensTable.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No tokens generated.</td></tr>';
            }

            // 2. Check for Lexical Errors
            if (result.lexical_errors && result.lexical_errors.length > 0) {
                showCompilationErrors(result.lexical_errors, 'lexer');
                return;
            }

            // 3. Process Syntactic Analysis (AST)
            renderAST(result.ast);

            // 4. Check for Syntax Errors
            if (result.syntax_errors && result.syntax_errors.length > 0) {
                showCompilationErrors(result.syntax_errors, 'parser');
                return;
            }

            // 5. Process Semantic Analysis (Symbol Table)
            symbolTableBody.innerHTML = '';
            if (result.symbol_table && result.symbol_table.length > 0) {
                result.symbol_table.forEach(sym => {
                    const row = document.createElement('tr');
                    const typeClass = sym.type === 'int' ? 'type-int' : (sym.type === 'float' ? 'type-float' : '');
                    row.innerHTML = `
                        <td class="font-mono">${sym.name}</td>
                        <td><span class="type-badge ${typeClass}">${sym.type}</span></td>
                        <td>${sym.scope}</td>
                        <td>Line ${sym.line}</td>
                    `;
                    symbolTableBody.appendChild(row);
                });
            } else {
                symbolTableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Symbol table is empty.</td></tr>';
            }

            // 6. Check for Semantic Errors
            if (result.semantic_errors && result.semantic_errors.length > 0) {
                showCompilationErrors(result.semantic_errors, 'semantic');
                return;
            }

            // 7. Update TAC Tab
            tacCode.textContent = result.tac && result.tac.length > 0 ? result.tac.join('\n') : '; Empty TAC';

            // 8. Update Optimization Tab
            preOptTacCode.textContent = result.tac && result.tac.length > 0 ? result.tac.join('\n') : '; Empty TAC';
            postOptTacCode.textContent = result.optimized_tac && result.optimized_tac.length > 0 ? result.optimized_tac.join('\n') : '; Empty Optimized TAC';
            
            optLogsList.innerHTML = '';
            if (result.optimization_logs && result.optimization_logs.length > 0) {
                result.optimization_logs.forEach(log => {
                    const li = document.createElement('li');
                    li.textContent = log;
                    optLogsList.appendChild(li);
                });
            } else {
                optLogsList.innerHTML = '<li class="text-muted">No optimizations performed. (Already optimal)</li>';
            }

            // 9. Update Target Code (Pseudo-Assembly)
            targetCodeBlock.textContent = result.target_code && result.target_code.length > 0 ? result.target_code.join('\n') : '; No target assembly generated';

            // 9.5 Render the Control Flow Graph (CFG) via D3.js
            renderCFG(result.cfg);

            // 10. Update Status Banner and Visual Flow
            statusIndicator.className = 'status-badge status-success';
            statusIndicator.textContent = 'SUCCESS';
            updatePipelineVisual('target', 'success');

            // Hide Errors, show success message
            compSuccessMsg.style.display = 'block';
            compErrorMsg.style.display = 'none';

        } catch (e) {
            console.error("Compilation process failed", e);
            statusIndicator.className = 'status-badge status-error';
            statusIndicator.textContent = 'CRASH';
            showCompilationErrors([{ message: `Connection error / Network issue: ${e.message}`, line: 1, column: 1 }], 'parser');
        }
    });

    // Initialize Page Content
    loadSamples();
}
