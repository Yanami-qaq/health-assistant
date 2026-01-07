/* app/static/js/chat.js */

const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// 🔥 新增：本地维护历史记录上下文
// 结构: [{role: "user", content: "A"}, {role: "assistant", content: "B"}]
let chatHistory = [];

// 保存用户健康目标
function saveGoalType() {
    const select = document.getElementById('goalTypeSelect');
    if (!select) return;
    
    const goalType = select.value;
    
    fetch('/plan/save_goal', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({goal_type: goalType})
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // 静默保存，不显示提示
        } else {
            console.error('保存目标失败:', data.message);
        }
    })
    .catch(error => {
        console.error('保存目标错误:', error);
    });
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // 1. 禁用 UI，防止重复提交
    sendBtn.disabled = true;
    userInput.disabled = true;

    // 2. 显示并记录用户消息
    appendMessage('user', text);

    // 🔥 记录用户发言到历史
    chatHistory.push({ role: "user", content: text });

    userInput.value = '';

    // 3. 显示 AI 正在输入...
    const loadingId = appendLoading();

    // 4. 发送请求 (带上 History)
    fetch('/plan/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: text,
            // 🔥 发送最近 10 条历史，避免请求包体过大，也节省 Token
            history: chatHistory.slice(-10)
        })
    })
    .then(res => res.json())
    .then(data => {
        removeLoading(loadingId);
        if (data.status === 'success') {
            appendMessage('ai', data.reply);

            // 🔥 记录 AI 回复到历史
            chatHistory.push({ role: "assistant", content: data.reply });

            if (data.updated_plan) {
                showToast('✅ 每日清单已同步到仪表盘');
            }
        } else {
            appendMessage('ai', '🚫 ' + data.reply);
            // 如果出错，把刚才用户的那条记录也弹出来，保持一致性（可选）
            chatHistory.pop();
        }
    })
    .catch(err => {
        console.error(err);
        removeLoading(loadingId);
        appendMessage('ai', '❌ 网络连接错误，请检查服务器。');
        chatHistory.pop();
    })
    .finally(() => {
        // 恢复 UI
        sendBtn.disabled = false;
        userInput.disabled = false;
        userInput.focus();
    });
}

function appendMessage(role, text) {
    const wrapper = document.createElement('div');

    if (role === 'ai') {
        wrapper.className = 'message-wrapper message-ai';
        // 使用 marked 解析 Markdown (确保页面 head 中已引入 marked.js)
        // 如果没有 marked，就直接显示文本
        const parsedText = (typeof marked !== 'undefined') ? marked.parse(text) : text;

        wrapper.innerHTML = `
            <div class="ai-avatar"><i class="bi bi-robot"></i></div>
            <div class="bubble-ai">${parsedText}</div>
        `;
    } else {
        wrapper.className = 'message-wrapper message-user';
        // 用户输入纯文本，使用 textContent 防止 XSS 攻击
        wrapper.innerHTML = `
            <div class="user-avatar"><i class="bi bi-person-fill"></i></div>
            <div class="bubble-user"></div>
        `;
        wrapper.querySelector('.bubble-user').textContent = text;
    }

    chatBox.appendChild(wrapper);
    scrollToBottom();
}

function appendLoading() {
    const id = 'loading-' + Date.now();
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper message-ai';
    wrapper.id = id;

    // 🔥 使用新的 3 个跳动小点结构
    wrapper.innerHTML = `
        <div class="ai-avatar"><i class="bi bi-robot"></i></div>
        <div class="bubble-ai" style="padding: 10px 15px;">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
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
    // 简单的 Toast 提示，如果有 Bootstrap Toast 组件也可以在这里调用
    console.log("Toast:", msg);

    // 创建一个简单的临时提示框
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '10px 20px';
    toast.style.backgroundColor = '#198754';
    toast.style.color = 'white';
    toast.style.borderRadius = '5px';
    toast.style.zIndex = '9999';
    toast.innerText = msg;

    document.body.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3000);
}