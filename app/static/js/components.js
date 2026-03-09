/**
 * UI Components for the Meta-Analysis Agent chat interface.
 */

const Components = {
    /**
     * Add a message to the chat area.
     */
    addMessage(type, content, options = {}) {
        const messages = document.getElementById('messages');
        const msg = document.createElement('div');
        msg.className = `message ${type}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        if (options.html) {
            contentDiv.innerHTML = content;
        } else if (options.markdown && typeof marked !== 'undefined') {
            contentDiv.innerHTML = marked.parse(content);
        } else {
            contentDiv.innerHTML = `<p>${this._escapeHtml(content)}</p>`;
        }

        msg.appendChild(contentDiv);
        messages.appendChild(msg);
        this._scrollToBottom();
        return msg;
    },

    /**
     * Start or append to the current agent message bubble.
     * A new bubble is created if none is currently streaming.
     */
    appendToAgentMessage(text) {
        let current = document.querySelector('.message.agent-message.streaming');
        if (!current) {
            current = this.addMessage('agent', '', { html: true });
            current.classList.add('streaming');
            current._textBuffer = '';
        }

        current._textBuffer = (current._textBuffer || '') + text;
        const contentDiv = current.querySelector('.message-content');
        if (typeof marked !== 'undefined') {
            contentDiv.innerHTML = marked.parse(current._textBuffer);
        } else {
            contentDiv.innerHTML = `<p>${this._escapeHtml(current._textBuffer)}</p>`;
        }
        this._scrollToBottom();
        return current;
    },

    /**
     * Finalize the current streaming agent message (stop appending to it).
     */
    finalizeAgentMessage() {
        const current = document.querySelector('.message.agent-message.streaming');
        if (current) {
            current.classList.remove('streaming');
            const dots = current.querySelector('.loading-dots');
            if (dots) dots.remove();
        }
    },

    /**
     * Add a loading indicator to the current agent message.
     */
    addLoadingDots() {
        let current = document.querySelector('.message.agent-message.streaming');
        if (!current) {
            current = this.addMessage('agent', '', { html: true });
            current.classList.add('streaming');
            current._textBuffer = '';
        }

        if (!current.querySelector('.loading-dots')) {
            const dots = document.createElement('div');
            dots.className = 'loading-dots';
            dots.innerHTML = '<span></span><span></span><span></span>';
            current.querySelector('.message-content').appendChild(dots);
        }
        this._scrollToBottom();
    },

    /**
     * Remove loading dots from the current agent message.
     */
    removeLoadingDots() {
        const dots = document.querySelector('.message.agent-message.streaming .loading-dots');
        if (dots) dots.remove();
    },

    /**
     * Complete the oldest still-running tool indicator.
     * Called when the next agent_text arrives after a tool call.
     */
    completeFirstRunningIndicator() {
        const first = document.querySelector('.tool-indicator.running');
        if (first) {
            first.classList.remove('running');
            first.classList.add('complete');
        }
    },

    /**
     * Add a tool use indicator with contextual detail.
     *
     * Handles these tools specifically:
     *   Skill  → shows skill name from input.skill
     *   Bash   → shows truncated command from input.command
     *   Write  → shows filename from input.file_path
     *   Read   → shows filename from input.file_path
     */
    addToolIndicator(toolName, input) {
        const messages = document.getElementById('messages');
        const indicator = document.createElement('div');
        indicator.className = 'tool-indicator running';
        indicator.dataset.tool = toolName;

        const { label, detail } = this._formatToolLabel(toolName, input);

        const labelSpan = document.createElement('span');
        labelSpan.className = 'tool-label';
        labelSpan.textContent = label;
        indicator.appendChild(labelSpan);

        if (detail) {
            const detailSpan = document.createElement('span');
            detailSpan.className = 'tool-detail';
            detailSpan.textContent = detail;
            indicator.appendChild(detailSpan);
        }

        messages.appendChild(indicator);
        this._scrollToBottom();
        return indicator;
    },

    /**
     * Add a thinking/reasoning block (collapsible).
     */
    addThinkingBlock(text) {
        const messages = document.getElementById('messages');
        const block = document.createElement('div');
        block.className = 'thinking-block collapsed';
        block.innerHTML = `
            <span class="toggle-label">Reasoning</span>
            <p>${this._escapeHtml(text)}</p>
        `;
        block.addEventListener('click', () => {
            block.classList.toggle('collapsed');
        });
        messages.appendChild(block);
        this._scrollToBottom();
    },

    /**
     * Show the upload status bar.
     */
    showUploadStatus(result) {
        const status = document.getElementById('upload-status');
        status.classList.remove('hidden');
        status.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${getComputedStyle(document.documentElement).getPropertyValue('--success')}" stroke-width="2">
                <polyline points="20,6 9,17 4,12"/>
            </svg>
            <span class="filename">${this._escapeHtml(result.filename)}</span>
            <span class="outcome-count">${result.outcomes.length} outcome${result.outcomes.length !== 1 ? 's' : ''} found</span>
        `;
    },

    /**
     * Enable download buttons once analysis artifacts are available.
     */
    enableDownloads(sessionId, requestId) {
        const rmdBtn  = document.getElementById('btn-download-rmd');
        const jsonBtn = document.getElementById('btn-download-json');
        const runBtn  = document.getElementById('btn-download-run');

        rmdBtn.disabled = false;
        rmdBtn.onclick = () => {
            window.open(`/api/runs/${sessionId}/${requestId}/report.Rmd`, '_blank');
        };

        jsonBtn.disabled = false;
        jsonBtn.onclick = () => {
            window.open(`/api/runs/${sessionId}/${requestId}/final.json`, '_blank');
        };

        runBtn.disabled = false;
        runBtn.onclick = () => {
            // Trigger browser download of the full run zip
            const a = document.createElement('a');
            a.href = `/api/runs/${sessionId}/${requestId}/download`;
            a.download = `run_${sessionId}_${requestId}.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };
    },

    /**
     * Generate and display a text summary of the analysis results in the chat.
     * Called when the `visualization` SSE event is received.
     */
    addResultSummary(finalJson) {
        const outcomes = finalJson.outcomes || [];
        if (outcomes.length === 0) return;

        let md = '**Analysis complete.** Here are the key findings:\n\n';

        outcomes.forEach(outcome => {
            const p = outcome.pooled_random || outcome.pooled_estimate;
            const het = outcome.heterogeneity;
            const measure = outcome.measure || '';
            const isRatio = outcome.is_ratio ?? ['HR', 'RR', 'OR'].includes(measure);

            md += `### ${outcome.full_name || outcome.outcome_name} (${measure})\n`;

            const effect = p ? Number(p.effect ?? p.te) : NaN;
            if (!p || !isFinite(effect)) {
                const reason = outcome.interpretation || 'insufficient data for meta-analysis';
                md += `- *Skipped: ${reason}*\n\n`;
                return;
            }

            const lower  = Number(p.ci_lower ?? p.lower);
            const upper  = Number(p.ci_upper ?? p.upper);
            const pval   = Number(p.p_value  ?? p.pval);
            const pStr   = pval < 0.001 ? '< 0.001' : pval.toFixed(3);
            const sig    = pval < 0.05 ? ' ✓' : '';

            md += `- **Pooled ${measure}:** ${effect.toFixed(2)} (95% CI ${lower.toFixed(2)}–${upper.toFixed(2)}), p = ${pStr}${sig}\n`;

            if (het) {
                const i2 = Number(het.i2 ?? het.I2);
                const hetLabel = i2 < 25 ? 'low' : i2 < 50 ? 'moderate' : i2 < 75 ? 'substantial' : 'considerable';
                md += `- **Heterogeneity:** I² = ${i2.toFixed(1)}% (${hetLabel})\n`;
            }

            if (outcome.n_studies) {
                md += `- **Studies:** ${outcome.n_studies}\n`;
            }

            if (outcome.interpretation) {
                md += `\n${outcome.interpretation}\n`;
            }

            md += '\n';
        });

        this.addMessage('agent', md, { markdown: true });
    },

    // --- Helpers ---

    _scrollToBottom() {
        const chatArea = document.getElementById('chat-area');
        requestAnimationFrame(() => {
            chatArea.scrollTop = chatArea.scrollHeight;
        });
    },

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Derive a display label and optional detail string for a tool call.
     */
    _formatToolLabel(toolName, input) {
        switch (toolName) {
            case 'Skill': {
                const skillName = input?.skill || input?.name || 'unknown';
                return { label: `Skill: ${skillName}`, detail: null };
            }
            case 'Bash': {
                const cmd = (input?.command || '').trim();
                // Show first meaningful line, truncated
                const firstLine = cmd.split('\n').find(l => l.trim()) || cmd;
                const detail = firstLine.length > 72 ? firstLine.slice(0, 72) + '…' : firstLine;
                return { label: 'Bash', detail: detail || null };
            }
            case 'Write': {
                const fp = input?.file_path || '';
                return { label: 'Write', detail: fp.split('/').pop() || fp || null };
            }
            case 'Read': {
                const fp = input?.file_path || '';
                return { label: 'Read', detail: fp.split('/').pop() || fp || null };
            }
            default: {
                // Strip MCP prefix (e.g. mcp__abc123__tool_name → tool_name)
                const short = toolName.replace(/^mcp__[\w-]+__/, '');
                const aliases = {
                    'run_r_analysis': 'R Analysis',
                    'read_outcomes':  'Read Outcomes',
                    'doc_writer':     'Write File',
                    'doc_reader':     'Read File',
                };
                return { label: aliases[short] || short, detail: null };
            }
        }
    },
};
