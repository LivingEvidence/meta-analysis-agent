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
     * Start or append to the current agent message.
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
     * Finalize the current streaming agent message.
     */
    finalizeAgentMessage() {
        const current = document.querySelector('.message.agent-message.streaming');
        if (current) {
            current.classList.remove('streaming');
            // Remove loading dots if present
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

        // Only add if not already present
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
     * Add a tool use indicator.
     */
    addToolIndicator(toolName, input) {
        const messages = document.getElementById('messages');
        const indicator = document.createElement('div');
        indicator.className = 'tool-indicator running';
        indicator.dataset.tool = toolName;

        const displayName = this._formatToolName(toolName);
        let detail = '';
        if (input && input.outcome_name) {
            detail = ` (${input.outcome_name})`;
        }
        indicator.textContent = `${displayName}${detail}`;

        messages.appendChild(indicator);
        this._scrollToBottom();
        return indicator;
    },

    /**
     * Update a tool indicator to complete status.
     */
    completeToolIndicator(toolName) {
        const indicators = document.querySelectorAll(`.tool-indicator[data-tool="${toolName}"].running`);
        indicators.forEach(ind => {
            ind.classList.remove('running');
            ind.classList.add('complete');
        });
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
     * Enable download buttons.
     */
    enableDownloads(sessionId, requestId) {
        const rmdBtn = document.getElementById('btn-download-rmd');
        const jsonBtn = document.getElementById('btn-download-json');

        rmdBtn.disabled = false;
        rmdBtn.onclick = () => {
            window.open(`/api/runs/${sessionId}/${requestId}/report.Rmd`, '_blank');
        };

        jsonBtn.disabled = false;
        jsonBtn.onclick = () => {
            window.open(`/api/runs/${sessionId}/${requestId}/final.json`, '_blank');
        };
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

    _formatToolName(name) {
        const names = {
            'run_r_analysis': 'R Analysis',
            'read_outcomes': 'Read Outcomes',
            'doc_writer': 'Writing File',
            'doc_reader': 'Reading File',
        };
        // Strip MCP prefix if present
        const short = name.replace(/^mcp__\w+__/, '');
        return names[short] || short;
    }
};
