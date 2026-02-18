let chatHistory = [];
let isProcessing = false;
let selectedSources = new Set();

// DOM Elements
const uploadModal = document.getElementById('uploadModal');
const confirmModal = document.getElementById('confirmModal');
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

// Cleanup on window close/unload
window.addEventListener('beforeunload', async (e) => {
    e.preventDefault();
    e.returnValue = 'Are you sure you want to leave? All chat history and documents will be deleted.';
    
    // Clear all data
    try {
        await fetch('/clear-all', { method: 'DELETE', keepalive: true });
    } catch (error) {
        console.error('Error clearing data on exit:', error);
    }
    
    return e.returnValue;
});

// Show upload modal on load
window.addEventListener('load', () => {
    uploadModal.classList.add('active');
    loadDocuments();
});

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
                
                item.appendChild(checkbox);
                item.appendChild(label);
                documentList.appendChild(item);
                
                if (checkbox.checked) selectedSources.add(doc);
            });
            
            sendBtn.disabled = false;
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

// Send Message
async function sendMessage() {
    const question = chatInput.value.trim();
    if (!question || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    chatInput.disabled = true;

    // Add user message
    addMessage(question, 'user');
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Add thinking indicator
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'thinking';
    thinkingDiv.textContent = 'Thinking...';
    chatMessages.appendChild(thinkingDiv);
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

        thinkingDiv.remove();

        const answerDiv = document.createElement('div');
        answerDiv.className = 'message message-assistant';
        chatMessages.appendChild(answerDiv);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullAnswer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                const data = JSON.parse(line);

                if (data.type === 'token') {
                    fullAnswer += data.content;
                    try {
                        answerDiv.innerHTML = marked.parse(fullAnswer);
                    } catch {
                        answerDiv.textContent = fullAnswer;
                    }
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            }
        }

        chatHistory.push({ role: 'user', content: question });
        chatHistory.push({ role: 'assistant', content: fullAnswer });

    } catch (error) {
        thinkingDiv.remove();
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
            messageDiv.innerHTML = marked.parse(content);
        } catch {
            messageDiv.textContent = content;
        }
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
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
                chatMessages.innerHTML = '<div class="welcome-message"><h2>Welcome to NotebookLM Clone</h2><p>Upload PDF documents to get started</p></div>';
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