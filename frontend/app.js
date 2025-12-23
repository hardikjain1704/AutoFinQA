// ===================================
// Configuration & State Management
// ===================================
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
    ALLOWED_EXTENSIONS: ['.pdf', '.csv', '.xlsx', '.xls', '.docx', '.json', '.txt'],
    TYPING_DELAY: 300,
    TOAST_DURATION: 4000
};

const STATE = {
    currentMode: 'simple',
    sessionId: generateSessionId(),
    isProcessing: false,
    uploadedDocuments: [],
    chatHistory: {
        simple: [],
        agent: []
    }
};

// ===================================
// Utility Functions
// ===================================
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function getFileExtension(filename) {
    return '.' + filename.split('.').pop().toLowerCase();
}

function getFileIcon(filename) {
    const ext = getFileExtension(filename);
    const iconMap = {
        '.pdf': 'PDF',
        '.csv': 'CSV',
        '.xlsx': 'XLS',
        '.xls': 'XLS',
        '.docx': 'DOC',
        '.json': 'JSON',
        '.txt': 'TXT'
    };
    return iconMap[ext] || 'FILE';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// ===================================
// Toast Notifications
// ===================================
function showToast(message, type = 'info', title = '') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconSvg = {
        success: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>',
        error: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>',
        info: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>'
    };
    
    toast.innerHTML = `
        ${iconSvg[type]}
        <div class="toast-content">
            ${title ? `<div class="toast-title">${escapeHtml(title)}</div>` : ''}
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, CONFIG.TOAST_DURATION);
}

// ===================================
// API Functions
// ===================================
async function uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

async function askQuestion(query, mode = 'simple') {
    const endpoint = mode === 'agent' ? '/ask-agent' : '/ask';
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                session_id: STATE.sessionId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Query error:', error);
        throw error;
    }
}

// ===================================
// UI Update Functions
// ===================================
function updateDocumentList() {
    const listContainer = document.getElementById('document-list');
    
    if (STATE.uploadedDocuments.length === 0) {
        listContainer.innerHTML = '<div class="empty-state">No documents uploaded yet</div>';
        return;
    }
    
    listContainer.innerHTML = STATE.uploadedDocuments.map(doc => `
        <div class="document-item">
            <div class="document-icon">${getFileIcon(doc.name)}</div>
            <div class="document-info">
                <div class="document-name">${escapeHtml(doc.name)}</div>
                <div class="document-meta">${formatFileSize(doc.size)}</div>
            </div>
        </div>
    `).join('');
}

function addMessage(text, isUser = false, metadata = null) {
    const messagesContainer = document.getElementById('chat-messages');
    
    // Remove welcome message if it exists
    const welcomeMsg = messagesContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'message-user' : 'message-assistant'}`;
    
    let content = `
        <div class="message-content">
            <div class="message-text">${escapeHtml(text)}</div>
    `;
    
    // Add agent process if available
    if (metadata && metadata.agent_process) {
        content += renderAgentProcess(metadata.agent_process);
    }
    
    // Add sources if available
    if (metadata && metadata.sources && metadata.sources.length > 0) {
        content += renderSources(metadata.sources);
    }
    
    // Add metadata footer
    if (!isUser) {
        content += `
            <div class="message-meta">
                <span>${formatTimestamp()}</span>
                ${metadata && metadata.mode ? `<span>•</span><span>${metadata.mode === 'agent' ? 'Agentic RAG' : 'Simple RAG'}</span>` : ''}
            </div>
        `;
    }
    
    content += '</div>';
    messageDiv.innerHTML = content;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Store in history
    STATE.chatHistory[STATE.currentMode].push({
        text: text,
        isUser: isUser,
        metadata: metadata,
        timestamp: Date.now()
    });
}

function renderAgentProcess(process) {
    if (!process || !process.steps || process.steps.length === 0) return '';
    
    let html = `
        <div class="agent-process">
            <div class="agent-process-title">Reasoning Process</div>
    `;
    
    process.steps.forEach((step, index) => {
        html += `
            <div class="agent-step">
                <div class="agent-step-indicator">${index + 1}</div>
                <div class="agent-step-text">
                    ${escapeHtml(step.text)}
                    ${step.tool ? `<span class="agent-tool-badge">${escapeHtml(step.tool)}</span>` : ''}
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

function renderSources(sources) {
    if (!sources || sources.length === 0) return '';
    
    let html = `
        <div class="sources">
            <div class="sources-title">Sources</div>
    `;
    
    sources.forEach(source => {
        html += '<div class="source-item">';
        if (source.source) html += `<div><span class="source-label">Document:</span> <span class="source-value">${escapeHtml(source.source)}</span></div>`;
        if (source.page) html += `<div><span class="source-label">Page:</span> <span class="source-value">${source.page}</span></div>`;
        if (source.table_id) html += `<div><span class="source-label">Table ID:</span> <span class="source-value">${escapeHtml(source.table_id)}</span></div>`;
        if (source.row_number !== undefined) html += `<div><span class="source-label">Row:</span> <span class="source-value">${source.row_number}</span></div>`;
        html += '</div>';
    });
    
    html += '</div>';
    return html;
}

function setProcessing(isProcessing) {
    STATE.isProcessing = isProcessing;
    const sendBtn = document.getElementById('send-btn');
    const chatInput = document.getElementById('chat-input');
    const typingIndicator = document.getElementById('typing-indicator');
    
    sendBtn.disabled = isProcessing || !chatInput.value.trim();
    chatInput.disabled = isProcessing;
    typingIndicator.style.display = isProcessing ? 'flex' : 'none';
}

function clearChat() {
    STATE.chatHistory[STATE.currentMode] = [];
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Chat Cleared</h2>
            <p>Start a new conversation by asking a question about your financial documents.</p>
        </div>
    `;
}

function switchMode(mode) {
    STATE.currentMode = mode;
    
    // Update button states
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    
    // Reload chat history for current mode
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = '';
    
    if (STATE.chatHistory[mode].length === 0) {
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <h2>Welcome to AutoFinQA</h2>
                <p>Upload your financial documents and start asking questions. You're currently in <strong>${mode === 'agent' ? 'Agentic RAG' : 'Simple RAG'}</strong> mode.</p>
            </div>
        `;
    } else {
        STATE.chatHistory[mode].forEach(msg => {
            addMessage(msg.text, msg.isUser, msg.metadata);
        });
    }
    
    showToast(`Switched to ${mode === 'agent' ? 'Agentic RAG' : 'Simple RAG'} mode`, 'info');
}

// ===================================
// Event Handlers
// ===================================
function handleFileSelect(files) {
    const validFiles = Array.from(files).filter(file => {
        const ext = getFileExtension(file.name);
        if (!CONFIG.ALLOWED_EXTENSIONS.includes(ext)) {
            showToast(`Invalid file type: ${file.name}`, 'error');
            return false;
        }
        if (file.size > CONFIG.MAX_FILE_SIZE) {
            showToast(`File too large: ${file.name}`, 'error');
            return false;
        }
        return true;
    });
    
    if (validFiles.length === 0) return;
    
    validFiles.forEach(file => uploadFile(file));
}

async function uploadFile(file) {
    const statusContainer = document.getElementById('upload-status');
    const progressId = 'progress_' + Date.now();
    
    // Create progress element
    const progressDiv = document.createElement('div');
    progressDiv.id = progressId;
    progressDiv.className = 'upload-progress';
    progressDiv.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-size: 0.875rem; font-weight: 500;">${escapeHtml(file.name)}</span>
            <span style="font-size: 0.75rem; color: var(--gray-500);">Uploading...</span>
        </div>
        <div class="upload-progress-bar">
            <div class="upload-progress-fill" style="width: 0%"></div>
        </div>
    `;
    statusContainer.appendChild(progressDiv);
    
    try {
        // Simulate progress (since we can't track real progress with fetch)
        const progressBar = progressDiv.querySelector('.upload-progress-fill');
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress > 90) progress = 90;
            progressBar.style.width = progress + '%';
        }, 200);
        
        const result = await uploadDocument(file);
        
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        
        // Add to uploaded documents
        STATE.uploadedDocuments.push({
            name: file.name,
            size: file.size,
            uploadedAt: Date.now()
        });
        
        updateDocumentList();
        showToast('Document uploaded successfully', 'success', file.name);
        
        setTimeout(() => progressDiv.remove(), 2000);
    } catch (error) {
        progressDiv.remove();
        showToast(error.message || 'Upload failed', 'error', file.name);
    }
}

async function handleSendMessage(query) {
    if (!query.trim() || STATE.isProcessing) return;
    
    // Add user message
    addMessage(query, true);
    
    // Clear input
    document.getElementById('chat-input').value = '';
    updateSendButton();
    
    // Set processing state
    setProcessing(true);
    
    try {
        const response = await askQuestion(query, STATE.currentMode);
        
        // Parse response based on mode
        let answerText = '';
        let metadata = { mode: STATE.currentMode };
        
        if (STATE.currentMode === 'agent') {
            // Agent mode response structure
            answerText = response.answer || response.response || 'No answer received';
            
            // Extract agent process if available
            if (response.agent_process || response.intermediate_steps) {
                metadata.agent_process = parseAgentProcess(response);
            }
        } else {
            // Simple mode response structure
            answerText = response.answer || response.response || 'No answer received';
        }
        
        // Extract sources if available
        if (response.sources) {
            metadata.sources = response.sources;
        } else if (response.source_documents) {
            metadata.sources = response.source_documents.map(doc => ({
                source: doc.metadata?.source || 'Unknown',
                page: doc.metadata?.page,
                table_id: doc.metadata?.table_id,
                row_number: doc.metadata?.row_number
            }));
        }
        
        addMessage(answerText, false, metadata);
    } catch (error) {
        showToast(error.message || 'Failed to get answer', 'error');
        addMessage('Sorry, I encountered an error processing your request. Please try again.', false, { mode: STATE.currentMode });
    } finally {
        setProcessing(false);
    }
}

function parseAgentProcess(response) {
    const steps = [];
    
    // Try to extract intermediate steps
    if (response.intermediate_steps && Array.isArray(response.intermediate_steps)) {
        response.intermediate_steps.forEach((step, index) => {
            if (typeof step === 'object') {
                steps.push({
                    text: step.action || step.thought || `Step ${index + 1}`,
                    tool: step.tool || step.action_input?.tool
                });
            }
        });
    }
    
    // Try to extract from scratchpad
    if (response.scratchpad && typeof response.scratchpad === 'string') {
        const lines = response.scratchpad.split('\n').filter(line => line.trim());
        lines.forEach(line => {
            if (line.includes('Action:') || line.includes('Thought:') || line.includes('Observation:')) {
                const toolMatch = line.match(/Action:\s*(\w+)/);
                steps.push({
                    text: line.trim(),
                    tool: toolMatch ? toolMatch[1] : null
                });
            }
        });
    }
    
    // Fallback: create generic steps
    if (steps.length === 0 && response.answer) {
        steps.push({ text: 'Analyzed query and retrieved relevant information', tool: 'search' });
        steps.push({ text: 'Generated response based on retrieved context', tool: null });
    }
    
    return { steps };
}

function updateSendButton() {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = !chatInput.value.trim() || STATE.isProcessing;
}

// ===================================
// Event Listeners
// ===================================
document.addEventListener('DOMContentLoaded', () => {
    // Session ID input
    const sessionInput = document.getElementById('session-input');
    sessionInput.value = STATE.sessionId;
    sessionInput.addEventListener('change', (e) => {
        STATE.sessionId = e.target.value || generateSessionId();
    });
    
    // New session button
    document.getElementById('new-session-btn').addEventListener('click', () => {
        if (STATE.chatHistory[STATE.currentMode].length > 0) {
            if (!confirm('Creating a new session will end the current session and clear all chat history. Continue?')) {
                return;
            }
        }
        
        // Generate new session ID
        const oldSessionId = STATE.sessionId;
        STATE.sessionId = generateSessionId();
        sessionInput.value = STATE.sessionId;
        
        // Clear all chat history for both modes
        STATE.chatHistory.simple = [];
        STATE.chatHistory.agent = [];
        
        // Reset processing state
        STATE.isProcessing = false;
        
        // Clear the chat display
        clearChat();
        
        // Reset any ongoing operations
        const typingIndicator = document.getElementById('typing-indicator');
        typingIndicator.style.display = 'none';
        
        showToast(`Session ended. New session started.`, 'success');
        console.log(`Session switched: ${oldSessionId} → ${STATE.sessionId}`);
    });
    
    // Upload zone
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    
    uploadZone.addEventListener('click', () => fileInput.click());
    
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFileSelect(e.dataTransfer.files);
    });
    
    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files);
        fileInput.value = ''; // Reset input
    });
    
    // Mode selector
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchMode(btn.dataset.mode);
        });
    });
    
    // Dark mode toggle
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const sunIcon = darkModeToggle.querySelector('.sun-icon');
    const moonIcon = darkModeToggle.querySelector('.moon-icon');
    
    // Check for saved theme preference or default to light mode
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    if (currentTheme === 'dark') {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    }
    
    darkModeToggle.addEventListener('click', () => {
        const theme = document.documentElement.getAttribute('data-theme');
        const newTheme = theme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        if (newTheme === 'dark') {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
            showToast('Dark mode enabled', 'info');
        } else {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
            showToast('Light mode enabled', 'info');
        }
    });
    
    // Chat input
    const chatInput = document.getElementById('chat-input');
    chatInput.addEventListener('input', () => {
        updateSendButton();
        // Auto-resize textarea
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('chat-form').dispatchEvent(new Event('submit'));
        }
    });
    
    // Chat form submit
    document.getElementById('chat-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (query) {
            handleSendMessage(query);
        }
    });
    
    // Initialize
    updateDocumentList();
    showToast('Welcome to AutoFinQA', 'info');
});
