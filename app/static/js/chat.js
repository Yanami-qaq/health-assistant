/* app/static/js/chat.js */

const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // 1. 禁用 UI
    sendBtn.disabled = true;
    userInput.disabled = true;

    // 2. 显示用户消息
    appendMessage('user', text);
    userInput.value = '';

    // 3. 显示 AI 正在输入...
    const loadingId = appendLoading();

    // 4. 发送请求
    fetch('/plan/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        removeLoading(loadingId);
        if (data.status === 'success') {
            appendMessage('ai', data.reply);
            if (data.updated_plan) {
                showToast('✅ 每日清单已同步到仪表盘');
            }
        } else {
            appendMessage('ai', '🚫 ' + data.reply);
        }
    })
    .catch(err => {
        console.error(err);
        removeLoading(loadingId);
        appendMessage('ai', '❌ 网络连接错误，请检查服务器。');
    })
    .finally(() => {
        sendBtn.disabled = false;
        userInput.disabled = false;
        userInput.focus();
    });
}

function appendMessage(role, text) {
    const wrapper = document.createElement('div');
    if (role === 'ai') {
        wrapper.className = 'message-wrapper message-ai';
        // 使用 marked 解析 Markdown
        const parsedText = marked.parse(text);
        wrapper.innerHTML = `
            <div class="ai-avatar"><i class="bi bi-robot"></i></div>
            <div class="bubble-ai">${parsedText}</div>
        `;
    } else {
        wrapper.className = 'message-wrapper message-user';
        wrapper.innerHTML = `
            <div class="user-avatar"><i class="bi bi-person-fill"></i></div>
            <div class="bubble-user">${text}</div>
        `;
    }
    chatBox.appendChild(wrapper);
    scrollToBottom();
}

function appendLoading() {
    const id = 'loading-' + Date.now();
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper message-ai';
    wrapper.id = id;
    wrapper.innerHTML = `
        <div class="ai-avatar"><i class="bi bi-robot"></i></div>
        <div class="bubble-ai">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    chatBox.appendChild(wrapper);
    scrollToBottom();
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'smooth' });
}

function showToast(msg) {
    // 简单实现
    console.log(msg);
}