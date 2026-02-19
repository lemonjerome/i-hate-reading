let chatHistory = [];
let isProcessing = false;
let selectedSources = new Set();

// DOM Elements
const uploadModal = document.getElementById('uploadModal');
const confirmModal = document.getElementById('confirmModal');
const tutorialModal = document.getElementById('tutorialModal');
const uploadBtn = document.getElementById('uploadBtn');
const closeModal = document.querySelector('.close');
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadProgress = document.getElementById('uploadProgress');
const progressFill = document.getElementById('progressFill');
const uploadStatus = document.getElementById('uploadStatus');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const documentList = document.getElementById('documentList');
const clearChatBtn = document.getElementById('clearChatBtn');
const newChatBtn = document.getElementById('newChatBtn');
const tutorialStartBtn = document.getElementById('tutorialStart');
const helpBtn = document.getElementById('helpBtn');

// Cleanup on window close/unload
window.addEventListener('beforeunload', (e) => {
    e.preventDefault();
    e.returnValue = 'Are you sure you want to leave? All chat history and documents will be deleted.';
    return e.returnValue;
});

// Actually clear data when user confirms leaving
window.addEventListener('pagehide', () => {
    navigator.sendBeacon('/cleanup');
});

// Show tutorial modal on load
window.addEventListener('load', () => {
    tutorialModal.classList.add('active');
    loadDocuments();
});

// Tutorial → Get Started opens upload modal
tutorialStartBtn.onclick = () => {
    tutorialModal.classList.remove('active');
    uploadModal.classList.add('active');
};

// Help button → reopen tutorial
helpBtn.onclick = () => tutorialModal.classList.add('active');

// Upload Modal Handlers
uploadBtn.onclick = () => uploadModal.classList.add('active');
closeModal.onclick = () => uploadModal.classList.remove('active');

dropZone.onclick = () => fileInput.click();

dropZone.ondragover = (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
};

dropZone.ondragleave = () => {
    dropZone.classList.remove('drag-over');
};

dropZone.ondrop = (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    
    // Filter only PDF files
    const pdfFiles = Array.from(files).filter(file => 
        file.name.toLowerCase().endsWith('.pdf')
    );
    
    if (pdfFiles.length === 0) {
        alert('Please upload only PDF files');
        return;
    }
    
    if (pdfFiles.length < files.length) {
        alert(`${files.length - pdfFiles.length} non-PDF file(s) were excluded`);
    }
    
    uploadFiles(pdfFiles);
};

fileInput.onchange = (e) => {
    const files = Array.from(e.target.files);
    
    // Validate all files are PDFs
    const nonPdfFiles = files.filter(file => 
        !file.name.toLowerCase().endsWith('.pdf')
    );
    
    if (nonPdfFiles.length > 0) {
        alert('Only PDF files are allowed');
        fileInput.value = '';
        return;
    }
    
    uploadFiles(files);
};

// Upload Files
async function uploadFiles(files) {
    if (files.length === 0) return;

    uploadProgress.classList.remove('hidden');
    dropZone.style.display = 'none';
    document.body.style.pointerEvents = 'none';
    uploadProgress.style.pointerEvents = 'all';

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    try {
        uploadStatus.textContent = 'Uploading documents...';
        progressFill.style.width = '30%';

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        uploadStatus.textContent = 'Embedding documents...';
        progressFill.style.width = '60%';

        const result = await response.json();
        
        // Check for errors
        const errors = result.results.filter(r => r.status === 'error');
        if (errors.length > 0) {
            const errorMsg = errors.map(e => `${e.filename}: ${e.message}`).join('\n');
            alert('Some files failed to upload:\n' + errorMsg);
        }

        uploadStatus.textContent = 'Processing complete!';
        progressFill.style.width = '100%';

        await loadDocuments();

        setTimeout(() => {
            uploadModal.classList.remove('active');
            uploadProgress.classList.add('hidden');
            dropZone.style.display = 'block';
            progressFill.style.width = '0%';
            document.body.style.pointerEvents = 'all';
            fileInput.value = '';
        }, 1000);

    } catch (error) {
        alert('Error uploading files: ' + error.message);
        uploadProgress.classList.add('hidden');
        dropZone.style.display = 'block';
        document.body.style.pointerEvents = 'all';
    }
}

// Load Documents
async function loadDocuments() {
    try {
        const response = await fetch('/documents');
        const data = await response.json();
        
        if (data.documents && data.documents.length > 0) {
            documentList.innerHTML = '';
            data.documents.forEach(doc => {
                const item = document.createElement('div');
                item.className = 'document-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `doc-${doc}`;
                checkbox.checked = true;
                checkbox.onchange = () => toggleDocument(doc, checkbox.checked);
                
                const label = document.createElement('label');
                label.htmlFor = `doc-${doc}`;
                label.textContent = doc;

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'doc-delete-btn';
                deleteBtn.innerHTML = '&times;';
                deleteBtn.title = 'Remove document';
                deleteBtn.onclick = async (e) => {
                    e.stopPropagation();
                    if (!confirm(`Remove "${doc}"?`)) return;
                    try {
                        await fetch(`/documents/${encodeURIComponent(doc)}`, { method: 'DELETE' });
                        selectedSources.delete(doc);
                        await loadDocuments();
                    } catch (err) {
                        alert('Error removing document: ' + err.message);
                    }
                };
                
                item.appendChild(checkbox);
                item.appendChild(label);
                item.appendChild(deleteBtn);
                documentList.appendChild(item);
                
                if (checkbox.checked) selectedSources.add(doc);
            });
            
            sendBtn.disabled = false;
        } else {
            documentList.innerHTML = '<p class="empty-state">No documents uploaded yet</p>';
            sendBtn.disabled = true;
        }
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function toggleDocument(doc, checked) {
    if (checked) {
        selectedSources.add(doc);
    } else {
        selectedSources.delete(doc);
    }
}

// Chat Input
chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = chatInput.scrollHeight + 'px';
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!isProcessing && chatInput.value.trim()) {
            sendMessage();
        }
    }
});

sendBtn.onclick = sendMessage;

// Format citations like [filename.pdf#3] or [source#2] into clickable badges
function formatCitations(html) {
    return html.replace(
        /\[([^\]<>]+?)#(\d+)\]/g,
        (match, filename, chunk) => {
            const encodedFile = encodeURIComponent(filename.trim());
            return `<a href="/view?file=${encodedFile}&chunk=${chunk}" target="_blank" class="citation-badge">${filename.trim()}#${chunk}</a>`;
        }
    );
}

// Render LaTeX in an element using KaTeX auto-render
function renderLatex(element) {
    if (!window.katexReady || typeof renderMathInElement === 'undefined') return;
    try {
        renderMathInElement(element, {
            delimiters: [
                { left: '$$', right: '$$', display: true },
                { left: '$',  right: '$',  display: false },
                { left: '\\(', right: '\\)', display: false },
                { left: '\\[', right: '\\]', display: true },
            ],
            throwOnError: false,
        });
    } catch (e) {
        // Silently ignore KaTeX errors
    }
}

// Safely parse markdown while preserving LaTeX from being mangled by marked.js.
// Strategy: extract all math regions into a map, replace with placeholders,
// run marked.parse, then restore the original math text before KaTeX runs.
function safeMarkdownParse(text) {
    const math = {};
    let idx = 0;
    const placeholder = (i) => `\x02MATH${i}\x03`;

    // Extract $$...$$ display blocks first (greedier, must come before $...$)
    let safe = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, content) => {
        const key = placeholder(idx++);
        math[key] = `$$${content}$$`;
        return key;
    });

    // Extract $...$ inline (not crossing newlines, non-empty)
    safe = safe.replace(/\$([^\$\n]+?)\$/g, (_, content) => {
        const key = placeholder(idx++);
        math[key] = `$${content}$`;
        return key;
    });

    // Extract \[...\] and \(...\)
    safe = safe.replace(/\\\[([\s\S]+?)\\\]/g, (_, content) => {
        const key = placeholder(idx++);
        math[key] = `\\[${content}\\]`;
        return key;
    });
    safe = safe.replace(/\\\((.+?)\\\)/g, (_, content) => {
        const key = placeholder(idx++);
        math[key] = `\\(${content}\\)`;
        return key;
    });

    // Parse markdown (math is safely hidden behind placeholders)
    let html = marked.parse(safe);

    // Restore math expressions (HTML-decode the placeholder wrappers if needed)
    html = html.replace(/\x02MATH(\d+)\x03/g, (_, i) => math[placeholder(Number(i))] || '');

    return html;
}

// Send Message (retryUserDiv: if provided, skip creating a new user bubble — used for retry)
async function sendMessage(retryUserDiv) {
    const question = chatInput.value.trim();
    if (!question || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    chatInput.disabled = true;

    // Add user message (skip if retrying)
    const userMsgDiv = retryUserDiv || addMessage(question, 'user');
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Add status indicator
    const statusDiv = document.createElement('div');
    statusDiv.className = 'status-indicator';
    statusDiv.innerHTML = `
        <span class="status-dot"></span>
        <span class="status-text">Starting...</span>
    `;
    chatMessages.appendChild(statusDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                chat_history: chatHistory.slice(-6),
                selected_sources: Array.from(selectedSources)
            })
        });

        statusDiv.remove();

        const answerDiv = document.createElement('div');
        answerDiv.className = 'message message-assistant';
        chatMessages.appendChild(answerDiv);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullAnswer = '';
        let firstToken = true;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                const data = JSON.parse(line);

                if (data.type === 'status') {
                    // Update status indicator text (re-add if removed)
                    if (!statusDiv.parentNode) {
                        chatMessages.insertBefore(statusDiv, answerDiv);
                    }
                    statusDiv.querySelector('.status-text').textContent = data.message;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }

                if (data.type === 'token') {
                    // Remove status on first token
                    if (firstToken) {
                        statusDiv.remove();
                        firstToken = false;
                    }
                    fullAnswer += data.content;
                    try {
                        answerDiv.innerHTML = formatCitations(safeMarkdownParse(fullAnswer));
                        renderLatex(answerDiv);
                    } catch {
                        answerDiv.textContent = fullAnswer;
                    }
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            }
        }

        chatHistory.push({ role: 'user', content: question });
        chatHistory.push({ role: 'assistant', content: fullAnswer });

        // Add action bar (retry + delete) under the answer
        const actionBar = createActionBar(question, userMsgDiv, answerDiv);
        chatMessages.appendChild(actionBar);
        chatMessages.scrollTop = chatMessages.scrollHeight;

    } catch (error) {
        statusDiv.remove();
        addMessage('Error: ' + error.message, 'assistant');
    }

    isProcessing = false;
    sendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
}

function addMessage(content, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';

    if (role === 'user') {
        messageDiv.innerHTML = `<div class="message-user">${content}</div>`;
    } else {
        messageDiv.className = 'message message-assistant';
        try {
            messageDiv.innerHTML = safeMarkdownParse(content);
            renderLatex(messageDiv);
        } catch {
            messageDiv.textContent = content;
        }
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return messageDiv;
}

// Clear Chat
clearChatBtn.onclick = () => {
    showConfirmModal(
        'Clear Chat History',
        'Are you sure you want to clear the chat history?',
        () => {
            chatHistory = [];
            chatMessages.innerHTML = '<div class="welcome-message"><h2>Chat Cleared</h2><p>Start a new conversation</p></div>';
        }
    );
};

// New Chat
newChatBtn.onclick = () => {
    showConfirmModal(
        'Start New Chat',
        'This will clear chat history and all documents. Continue?',
        async () => {
            try {
                await fetch('/clear-all', { method: 'DELETE' });
                chatHistory = [];
                selectedSources.clear();
                chatMessages.innerHTML = '<div class="welcome-message"><h2>Welcome to I Hate Reading</h2><p>A Local NotebookLM Clone by lemonjerome.</p></div>';
                documentList.innerHTML = '<p class="empty-state">No documents uploaded yet</p>';
                sendBtn.disabled = true;
                uploadModal.classList.add('active');
            } catch (error) {
                alert('Error clearing data: ' + error.message);
            }
        }
    );
};

// Confirmation Modal
function showConfirmModal(title, message, onConfirm) {
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    confirmModal.classList.add('active');

    document.getElementById('confirmYes').onclick = () => {
        confirmModal.classList.remove('active');
        onConfirm();
    };

    document.getElementById('confirmNo').onclick = () => {
        confirmModal.classList.remove('active');
    };
}

// Create action bar with retry and delete buttons for a chat exchange
function createActionBar(originalQuestion, userMsgDiv, answerDiv) {
    const bar = document.createElement('div');
    bar.className = 'message-actions';

    // Retry button
    const retryBtn = document.createElement('button');
    retryBtn.className = 'action-btn';
    retryBtn.title = 'Retry this question';
    retryBtn.innerHTML = '&#x21bb;'; // ↻
    retryBtn.onclick = () => {
        if (isProcessing) return;
        // Remove the answer and action bar, keep user bubble
        const uIdx = chatHistory.findLastIndex(h => h.role === 'user' && h.content === originalQuestion);
        if (uIdx >= 0) chatHistory.splice(uIdx, 2);
        answerDiv.remove();
        bar.remove();
        // Re-send the same question, reusing existing user bubble
        chatInput.value = originalQuestion;
        sendMessage(userMsgDiv);
    };

    // Delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'action-btn action-btn-delete';
    deleteBtn.title = 'Delete this exchange';
    deleteBtn.innerHTML = '&#x1F5D1;'; // 🗑
    deleteBtn.onclick = () => {
        // Remove from chatHistory
        const uIdx = chatHistory.findLastIndex(h => h.role === 'user' && h.content === originalQuestion);
        if (uIdx >= 0) chatHistory.splice(uIdx, 2);
        // Remove DOM elements
        if (userMsgDiv) userMsgDiv.remove();
        answerDiv.remove();
        bar.remove();
    };

    bar.appendChild(retryBtn);
    bar.appendChild(deleteBtn);
    return bar;
}