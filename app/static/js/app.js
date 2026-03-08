/**
 * Main Application Logic
 *
 * Manages state, SSE streaming, file upload, and chat form handling.
 */

const App = {
    state: {
        sessionId: null,
        requestId: null,
        fileId: null,
        fileName: null,
        outcomes: null,
        isProcessing: false,
        finalJson: null,
    },

    init() {
        this._bindUpload();
        this._bindChatForm();
        this._bindKeyboard();
    },

    // ============================
    // File Upload
    // ============================
    _bindUpload() {
        const uploadBtn = document.getElementById('btn-upload');
        const fileInput = document.getElementById('file-input');

        uploadBtn.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Uploading...';

            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error(`Upload failed: ${response.statusText}`);
                }

                const result = await response.json();
                this.state.fileId = result.file_id;
                this.state.fileName = result.filename;
                this.state.outcomes = result.outcomes;

                Components.showUploadStatus(result);
                Components.addMessage('system',
                    `Uploaded <strong>${result.filename}</strong> with ${result.outcomes.length} outcome(s): ` +
                    result.outcomes.map(o => `${o.name} (${o.full_name})`).join(', '),
                    { html: true }
                );
            } catch (err) {
                Components.addMessage('error', `Upload failed: ${err.message}`);
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                        <polyline points="17,8 12,3 7,8"/>
                        <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    Upload Data`;
                fileInput.value = '';
            }
        });
    },

    // ============================
    // Chat Form
    // ============================
    _bindChatForm() {
        const form = document.getElementById('chat-form');
        const input = document.getElementById('chat-input');

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = input.value.trim();
            if (!message || this.state.isProcessing) return;

            input.value = '';
            input.style.height = 'auto';
            this._sendMessage(message);
        });
    },

    _bindKeyboard() {
        const input = document.getElementById('chat-input');

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('chat-form').dispatchEvent(new Event('submit'));
            }
        });

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });
    },

    // ============================
    // SSE Message Handling
    // ============================
    async _sendMessage(message) {
        this.state.isProcessing = true;
        this._updateSendButton();

        Components.addMessage('user', message);
        Components.addLoadingDots();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.state.sessionId,
                    message: message,
                    file_id: this.state.fileId,
                }),
            });

            if (!response.ok) {
                throw new Error(`Request failed: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let eventName = null;
            let dataLines = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split(/\r?\n/);
                buffer = lines.pop(); // Keep incomplete line

                for (const line of lines) {
                    if (line === '') {
                        if (!eventName) {
                            dataLines = [];
                            continue;
                        }

                        try {
                            const data = JSON.parse(dataLines.join('\n'));
                            this._handleSSEEvent(eventName, data);
                        } catch (parseErr) {
                            console.warn('Failed to parse SSE data:', dataLines.join('\n'));
                        }
                        eventName = null;
                        dataLines = [];
                        continue;
                    }

                    if (line.startsWith('event: ')) {
                        eventName = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        dataLines.push(line.slice(6));
                    }
                }
            }
        } catch (err) {
            Components.removeLoadingDots();
            Components.finalizeAgentMessage();
            Components.addMessage('error', `Error: ${err.message}`);
        } finally {
            this.state.isProcessing = false;
            this._updateSendButton();
            Components.finalizeAgentMessage();
        }
    },

    _handleSSEEvent(event, data) {
        switch (event) {
            case 'session_init':
                this.state.sessionId = data.session_id;
                this.state.requestId = data.request_id;
                break;

            case 'agent_text':
                Components.removeLoadingDots();
                Components.appendToAgentMessage(data.text);
                break;

            case 'agent_thinking':
                Components.addThinkingBlock(data.text);
                break;

            case 'tool_use':
                Components.addToolIndicator(data.tool, data.input);
                break;

            case 'tool_result':
                if (data.tool) {
                    Components.completeToolIndicator(data.tool);
                }
                break;

            case 'subagent_start':
                Components.addSubagentIndicator(data.name, data.task || '');
                break;

            case 'subagent_end':
                // Subagent completed — nothing specific to do
                break;

            case 'visualization':
                this.state.finalJson = data;
                Visualizations.renderAll(data);
                if (this.state.sessionId && this.state.requestId) {
                    Components.enableDownloads(this.state.sessionId, this.state.requestId);
                }
                break;

            case 'artifact':
                if (data.type === 'report' && this.state.sessionId && this.state.requestId) {
                    Components.enableDownloads(this.state.sessionId, this.state.requestId);
                }
                break;

            case 'result':
                Components.removeLoadingDots();
                if (data.result) {
                    Components.appendToAgentMessage(data.result);
                    Components.finalizeAgentMessage();
                }
                if (data.cost_usd != null) {
                    console.log(`Agent completed: ${data.turns} turns, $${data.cost_usd?.toFixed(4)}, ${data.duration_ms}ms`);
                }
                break;

            case 'done':
                Components.removeLoadingDots();
                Components.finalizeAgentMessage();
                break;

            case 'error':
                Components.removeLoadingDots();
                Components.finalizeAgentMessage();
                Components.addMessage('error', data.message || 'An error occurred');
                break;

            default:
                console.log('Unknown SSE event:', event, data);
        }
    },

    _updateSendButton() {
        const btn = document.getElementById('btn-send');
        btn.disabled = this.state.isProcessing;
        if (this.state.isProcessing) {
            btn.style.opacity = '0.5';
        } else {
            btn.style.opacity = '1';
        }
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => App.init());
