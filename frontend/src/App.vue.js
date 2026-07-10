/// <reference types="D:/Project/bio-agent/frontend/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="D:/Project/bio-agent/frontend/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, nextTick, watch } from "vue";
import { runResearchStream } from "./services/api";
import AdminPanel from "./components/AdminPanel.vue";
// 登录状态
const isLoggedIn = ref(false);
const username = ref("");
const loading = ref(false);
const error = ref("");
// 聊天状态
const currentView = ref("chat");
const chatHistory = ref([]);
const currentChatIndex = ref(-1);
const inputMessage = ref("");
// 任务清单
const taskList = ref([]);
// 消息容器引用
const messagesContainer = ref(null);
// 计算当前对话
const currentChat = computed(() => {
    if (currentChatIndex.value >= 0 && currentChatIndex.value < chatHistory.value.length) {
        return chatHistory.value[currentChatIndex.value];
    }
    return null;
});
const currentMessages = computed(() => currentChat.value?.messages || []);
const currentChatTitle = computed(() => {
    if (!currentChat.value)
        return "新对话";
    return currentChat.value.title;
});
// 获取格式化时间
function getTimeString() {
    const now = new Date();
    return now.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}
function getDateString() {
    const now = new Date();
    return now.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}
// 获取任务状态文本
function getStatusText(status) {
    const statusMap = {
        pending: "待执行",
        in_progress: "执行中",
        completed: "已完成",
        error: "出错"
    };
    return statusMap[status] || status;
}
// 获取Agent头像样式类
function getAgentAvatarClass(agent) {
    const agentClassMap = {
        'master_agent': 'agent-master',
        'knowledge_agent': 'agent-knowledge',
        'automation_agent': 'agent-automation'
    };
    return agentClassMap[agent || ''] || 'agent-default';
}
// 获取Agent头像显示文本
function getAgentAvatarText(agent) {
    const agentTextMap = {
        'master_agent': '主',
        'knowledge_agent': '知',
        'automation_agent': '自'
    };
    return agentTextMap[agent || ''] || '助';
}
// 登录处理
async function handleLogin() {
    if (!username.value.trim()) {
        error.value = "请输入用户名";
        return;
    }
    loading.value = true;
    error.value = "";
    try {
        await new Promise(resolve => setTimeout(resolve, 500));
        loadChatHistory();
        isLoggedIn.value = true;
        if (chatHistory.value.length === 0) {
            startNewChat();
        }
        nextTick(() => {
            const textarea = document.querySelector("textarea");
            if (textarea)
                textarea.focus();
        });
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : "登录失败";
    }
    finally {
        loading.value = false;
    }
}
// 退出登录
function handleLogout() {
    saveChatHistory();
    isLoggedIn.value = false;
    username.value = "";
    chatHistory.value = [];
    currentChatIndex.value = -1;
    taskList.value = [];
}
// 开始新对话
function startNewChat() {
    currentView.value = "chat";
    const newChat = {
        title: "新对话",
        messages: [],
        lastMessage: "",
        timestamp: getDateString()
    };
    chatHistory.value.unshift(newChat);
    currentChatIndex.value = 0;
    inputMessage.value = "";
    taskList.value = [];
    nextTick(() => {
        const textarea = document.querySelector("textarea");
        if (textarea)
            textarea.focus();
    });
}
// 切换对话
function switchChat(index) {
    currentView.value = "chat";
    currentChatIndex.value = index;
    inputMessage.value = "";
    taskList.value = [];
    nextTick(() => {
        const textarea = document.querySelector("textarea");
        if (textarea)
            textarea.focus();
    });
}
// 删除对话
function deleteChat(index) {
    chatHistory.value.splice(index, 1);
    // 如果删除的是当前对话
    if (currentChatIndex.value === index) {
        if (chatHistory.value.length > 0) {
            // 切换到第一个对话
            currentChatIndex.value = 0;
        }
        else {
            // 没有对话了，创建一个新对话
            currentChatIndex.value = -1;
            startNewChat();
        }
    }
    else if (currentChatIndex.value > index) {
        // 如果删除的对话在当前对话之前，索引需要调整
        currentChatIndex.value -= 1;
    }
    taskList.value = [];
    saveChatHistory();
}
// 清空当前对话
function clearCurrentChat() {
    if (currentChat.value) {
        currentChat.value.messages = [];
        currentChat.value.lastMessage = "";
        taskList.value = [];
        saveChatHistory();
    }
}
// 发送消息
async function handleSend() {
    if (!inputMessage.value.trim() || loading.value || !currentChat.value) {
        return;
    }
    const userMessage = {
        content: inputMessage.value.trim(),
        isUser: true,
        timestamp: getTimeString()
    };
    currentChat.value.messages.push(userMessage);
    if (currentChat.value.messages.length === 1) {
        currentChat.value.title = inputMessage.value.trim().slice(0, 20) + (inputMessage.value.length > 20 ? "..." : "");
    }
    currentChat.value.lastMessage = inputMessage.value.trim().slice(0, 30) + (inputMessage.value.length > 30 ? "..." : "");
    currentChat.value.timestamp = getDateString();
    inputMessage.value = "";
    loading.value = true;
    taskList.value = [];
    await nextTick();
    scrollToBottom();
    try {
        // 构建对话历史
        const history = currentChat.value.messages.map((msg) => ({
            role: msg.isUser ? 'user' : 'assistant',
            content: msg.content
        }));
        await runResearchStream({ username: username.value, topic: userMessage.content, history }, (event) => {
            handleStreamEvent(event);
        });
    }
    catch (err) {
        const errorMessage = {
            content: err instanceof Error ? err.message : "发送消息失败，请重试",
            isUser: false,
            timestamp: getTimeString()
        };
        currentChat.value.messages.push(errorMessage);
        currentChat.value.lastMessage = "发送失败";
    }
    finally {
        loading.value = false;
        saveChatHistory();
        await nextTick();
        scrollToBottom();
    }
}
// 处理流式事件
function handleStreamEvent(event) {
    console.log("Stream event:", event);
    switch (event.type) {
        case "tasks":
            if (event.tasks && Array.isArray(event.tasks)) {
                taskList.value = event.tasks.map((task, index) => ({
                    id: index + 1,
                    step: task.step || index + 1,
                    agent: task.agent || "未知",
                    task_description: task.task_description || "",
                    status: "pending",
                    dependency: task.dependency || null
                }));
            }
            break;
        case "task_start":
            const startingTask = taskList.value.find(t => t.step === event.step);
            if (startingTask) {
                startingTask.status = "in_progress";
            }
            break;
        case "task_complete":
            const completedTask = taskList.value.find(t => t.step === event.step);
            if (completedTask) {
                completedTask.status = "completed";
                completedTask.result = event.result || event.summary || "";
            }
            break;
        case "task_error":
            const errorTask = taskList.value.find(t => t.step === event.step);
            if (errorTask) {
                errorTask.status = "error";
                errorTask.result = event.error || "执行失败";
            }
            break;
        case "summary":
        case "report":
            const botMessage = {
                content: event.content || event.report || "",
                isUser: false,
                timestamp: getTimeString()
            };
            if (currentChat.value) {
                currentChat.value.messages.push(botMessage);
                currentChat.value.lastMessage = botMessage.content.slice(0, 30) + (botMessage.content.length > 30 ? "..." : "");
                nextTick(() => scrollToBottom());
            }
            break;
        case "message_chunk":
            // 流式消息处理
            if (currentChat.value) {
                const agent = event.agent || '';
                const agentName = event.agent_name || '';
                // 查找当前Agent的消息（最后一条不是用户消息且agent匹配的消息）
                let currentMessage = currentChat.value.messages.filter(m => !m.isUser).pop();
                if (!currentMessage ||
                    currentMessage.agent !== agent ||
                    currentMessage.isComplete) {
                    // 创建新消息
                    const newMessage = {
                        content: event.content || "",
                        isUser: false,
                        timestamp: getTimeString(),
                        agent: agent || undefined,
                        agentName: agentName || undefined
                    };
                    newMessage.isComplete = false;
                    currentChat.value.messages.push(newMessage);
                }
                else {
                    // 更新现有消息
                    currentMessage.content += event.content || "";
                }
                // 标记完成
                if (event.complete) {
                    currentChat.value.messages.filter(m => !m.isUser).pop().isComplete = true;
                }
                currentChat.value.lastMessage = currentChat.value.messages[currentChat.value.messages.length - 1].content.slice(0, 30) + "...";
                nextTick(() => scrollToBottom());
            }
            break;
        case "message":
            const message = {
                content: event.content || "",
                isUser: false,
                timestamp: getTimeString(),
                agent: event.agent || undefined,
                agentName: event.agent_name || undefined
            };
            if (currentChat.value) {
                currentChat.value.messages.push(message);
                currentChat.value.lastMessage = message.content.slice(0, 30) + (message.content.length > 30 ? "..." : "");
                nextTick(() => scrollToBottom());
            }
            break;
        case "done":
            loading.value = false;
            break;
        case "error":
            const errorMsg = {
                content: event.detail || "执行出错",
                isUser: false,
                timestamp: getTimeString()
            };
            if (currentChat.value) {
                currentChat.value.messages.push(errorMsg);
            }
            loading.value = false;
            break;
    }
}
// 滚动到底部
function scrollToBottom() {
    if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
}
// 保存聊天历史到本地存储
function saveChatHistory() {
    if (!username.value)
        return;
    const data = {
        username: username.value,
        chats: chatHistory.value
    };
    localStorage.setItem(`bioagent_${username.value}`, JSON.stringify(data));
}
// 加载聊天历史
function loadChatHistory() {
    if (!username.value)
        return;
    const stored = localStorage.getItem(`bioagent_${username.value}`);
    if (stored) {
        try {
            const data = JSON.parse(stored);
            if (data.chats && Array.isArray(data.chats)) {
                chatHistory.value = data.chats;
                currentChatIndex.value = 0;
            }
        }
        catch (e) {
            console.error("加载聊天历史失败:", e);
        }
    }
}
// 监听聊天变化自动保存
watch(chatHistory, () => {
    if (isLoggedIn.value) {
        saveChatHistory();
    }
}, { deep: true });
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['app-shell']} */ ;
/** @type {__VLS_StyleScopedClasses['aurora']} */ ;
/** @type {__VLS_StyleScopedClasses['aurora']} */ ;
/** @type {__VLS_StyleScopedClasses['aurora']} */ ;
/** @type {__VLS_StyleScopedClasses['aurora']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-centered']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-form']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-form']} */ ;
/** @type {__VLS_StyleScopedClasses['logo']} */ ;
/** @type {__VLS_StyleScopedClasses['field']} */ ;
/** @type {__VLS_StyleScopedClasses['submit']} */ ;
/** @type {__VLS_StyleScopedClasses['submit']} */ ;
/** @type {__VLS_StyleScopedClasses['submit']} */ ;
/** @type {__VLS_StyleScopedClasses['secondary-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['error-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['user-info']} */ ;
/** @type {__VLS_StyleScopedClasses['logout-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['new-chat-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['delete-chat-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['delete-chat-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['message']} */ ;
/** @type {__VLS_StyleScopedClasses['user-avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['bot-avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['bot-avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['bot-avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['bot-avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['is-user']} */ ;
/** @type {__VLS_StyleScopedClasses['message-content']} */ ;
/** @type {__VLS_StyleScopedClasses['message-content']} */ ;
/** @type {__VLS_StyleScopedClasses['is-user']} */ ;
/** @type {__VLS_StyleScopedClasses['message-content']} */ ;
/** @type {__VLS_StyleScopedClasses['is-user']} */ ;
/** @type {__VLS_StyleScopedClasses['message-time']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-input-form']} */ ;
/** @type {__VLS_StyleScopedClasses['send-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['send-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['typing-dots']} */ ;
/** @type {__VLS_StyleScopedClasses['typing-dots']} */ ;
/** @type {__VLS_StyleScopedClasses['typing-dots']} */ ;
/** @type {__VLS_StyleScopedClasses['typing-dots']} */ ;
/** @type {__VLS_StyleScopedClasses['typing-indicator']} */ ;
/** @type {__VLS_StyleScopedClasses['task-panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['task-item']} */ ;
/** @type {__VLS_StyleScopedClasses['task-item']} */ ;
/** @type {__VLS_StyleScopedClasses['task-item']} */ ;
/** @type {__VLS_StyleScopedClasses['task-item']} */ ;
/** @type {__VLS_StyleScopedClasses['task-item']} */ ;
/** @type {__VLS_StyleScopedClasses['task-status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['pending']} */ ;
/** @type {__VLS_StyleScopedClasses['task-status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['in_progress']} */ ;
/** @type {__VLS_StyleScopedClasses['task-status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['completed']} */ ;
/** @type {__VLS_StyleScopedClasses['task-status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['task-result']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-task-list']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-task-list']} */ ;
/** @type {__VLS_StyleScopedClasses['messages-container']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['task-list']} */ ;
/** @type {__VLS_StyleScopedClasses['messages-container']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['task-list']} */ ;
/** @type {__VLS_StyleScopedClasses['messages-container']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
/** @type {__VLS_StyleScopedClasses['task-list']} */ ;
/** @type {__VLS_StyleScopedClasses['task-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.main, __VLS_intrinsics.main)({
    ...{ class: "app-shell" },
    ...{ class: ({ expanded: __VLS_ctx.isLoggedIn }) },
});
/** @type {__VLS_StyleScopedClasses['app-shell']} */ ;
/** @type {__VLS_StyleScopedClasses['expanded']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aurora" },
    'aria-hidden': "true",
});
/** @type {__VLS_StyleScopedClasses['aurora']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
if (!__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "layout layout-centered" },
    });
    /** @type {__VLS_StyleScopedClasses['layout']} */ ;
    /** @type {__VLS_StyleScopedClasses['layout-centered']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "panel panel-form panel-centered" },
    });
    /** @type {__VLS_StyleScopedClasses['panel']} */ ;
    /** @type {__VLS_StyleScopedClasses['panel-form']} */ ;
    /** @type {__VLS_StyleScopedClasses['panel-centered']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "panel-head" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "logo" },
    });
    /** @type {__VLS_StyleScopedClasses['logo']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
        viewBox: "0 0 24 24",
        'aria-hidden': "true",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
        d: "M12 2.5c-.7 0-1.4.2-2 .6L4.6 7C3.6 7.6 3 8.7 3 9.9v4.2c0 1.2.6 2.3 1.6 2.9l5.4 3.9c1.2.8 2.8.8 4 0l5.4-3.9c1-.7 1.6-1.7 1.6-2.9V9.9c0-1.2-.6-2.3-1.6-2.9L14 3.1a3.6 3.6 0 0 0-2-.6Z",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.handleLogin) },
        ...{ class: "form" },
    });
    /** @type {__VLS_StyleScopedClasses['form']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field" },
    });
    /** @type {__VLS_StyleScopedClasses['field']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.username),
        type: "text",
        placeholder: "请输入您的用户名",
        required: true,
        autocomplete: "username",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['form-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ class: "submit" },
        type: "submit",
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['submit']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "submit-label" },
    });
    /** @type {__VLS_StyleScopedClasses['submit-label']} */ ;
    if (__VLS_ctx.loading) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
            ...{ class: "spinner" },
            viewBox: "0 0 24 24",
            'aria-hidden': "true",
        });
        /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            cx: "12",
            cy: "12",
            r: "9",
            'stroke-width': "3",
        });
    }
    (__VLS_ctx.loading ? "登录中..." : "进入系统");
    if (__VLS_ctx.error) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "error-chip" },
        });
        /** @type {__VLS_StyleScopedClasses['error-chip']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
            viewBox: "0 0 20 20",
            'aria-hidden': "true",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
            d: "M10 3.2c-.3 0-.6.2-.8.5L3.4 15c-.4.7.1 1.6.8 1.6h11.6c.7 0 1.2-.9.8-1.6L10.8 3.7c-.2-.3-.5-.5-.8-.5Zm0 4.3c.4 0 .7.3.7.7v4c0 .4-.3.7-.7.7s-.7-.3-.7-.7V8.2c0-.4.3-.7.7-.7Zm0 6.6a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z",
        });
        (__VLS_ctx.error);
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "layout layout-fullscreen" },
    });
    /** @type {__VLS_StyleScopedClasses['layout']} */ ;
    /** @type {__VLS_StyleScopedClasses['layout-fullscreen']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
        ...{ class: "sidebar" },
    });
    /** @type {__VLS_StyleScopedClasses['sidebar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "sidebar-header" },
    });
    /** @type {__VLS_StyleScopedClasses['sidebar-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "user-info" },
    });
    /** @type {__VLS_StyleScopedClasses['user-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "user-avatar" },
    });
    /** @type {__VLS_StyleScopedClasses['user-avatar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    (__VLS_ctx.username.charAt(0).toUpperCase());
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    (__VLS_ctx.username);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "user-status" },
    });
    /** @type {__VLS_StyleScopedClasses['user-status']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.handleLogout) },
        ...{ class: "logout-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['logout-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
        viewBox: "0 0 24 24",
        width: "18",
        height: "18",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
        d: "M17 7l-5 5 5 5M7 7h12v10H7V7z",
        stroke: "currentColor",
        'stroke-width': "2",
        fill: "none",
        'stroke-linecap': "round",
        'stroke-linejoin': "round",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "sidebar-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['sidebar-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.startNewChat) },
        ...{ class: "new-chat-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['new-chat-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
        viewBox: "0 0 24 24",
        width: "18",
        height: "18",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
        d: "M12 5v14M5 12h14",
        stroke: "currentColor",
        'stroke-width': "2",
        fill: "none",
        'stroke-linecap': "round",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(!__VLS_ctx.isLoggedIn))
                    return;
                __VLS_ctx.currentView = 'admin';
                // @ts-ignore
                [isLoggedIn, isLoggedIn, handleLogin, username, username, username, loading, loading, loading, error, error, handleLogout, startNewChat, currentView,];
            } },
        ...{ class: "admin-btn" },
        ...{ class: ({ active: __VLS_ctx.currentView === 'admin' }) },
    });
    /** @type {__VLS_StyleScopedClasses['admin-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chat-history" },
    });
    /** @type {__VLS_StyleScopedClasses['chat-history']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
    for (const [chat, index] of __VLS_vFor((__VLS_ctx.chatHistory))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            ...{ onClick: (...[$event]) => {
                    if (!!(!__VLS_ctx.isLoggedIn))
                        return;
                    __VLS_ctx.switchChat(index);
                    // @ts-ignore
                    [currentView, chatHistory, switchChat,];
                } },
            key: (index),
            ...{ class: ({ active: __VLS_ctx.currentChatIndex === index }) },
        });
        /** @type {__VLS_StyleScopedClasses['active']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "chat-item-content" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-item-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "chat-preview" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-preview']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "chat-title" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-title']} */ ;
        (chat.title);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "chat-time" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-time']} */ ;
        (chat.timestamp);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "chat-last-message" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-last-message']} */ ;
        (chat.lastMessage);
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(!__VLS_ctx.isLoggedIn))
                        return;
                    __VLS_ctx.deleteChat(index);
                    // @ts-ignore
                    [currentChatIndex, deleteChat,];
                } },
            ...{ class: "delete-chat-btn" },
            title: "删除对话",
        });
        /** @type {__VLS_StyleScopedClasses['delete-chat-btn']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
            viewBox: "0 0 24 24",
            width: "14",
            height: "14",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
            d: "M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6",
            stroke: "currentColor",
            'stroke-width': "2",
            fill: "none",
            'stroke-linecap': "round",
            'stroke-linejoin': "round",
        });
        // @ts-ignore
        [];
    }
    if (__VLS_ctx.currentView === 'admin') {
        const __VLS_0 = AdminPanel;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({}));
        const __VLS_2 = __VLS_1({}, ...__VLS_functionalComponentArgsRest(__VLS_1));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "panel panel-chat" },
        });
        /** @type {__VLS_StyleScopedClasses['panel']} */ ;
        /** @type {__VLS_StyleScopedClasses['panel-chat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
            ...{ class: "chat-header" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "chat-title-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-title-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
        (__VLS_ctx.currentChatTitle);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "chat-controls" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-controls']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.clearCurrentChat) },
            ...{ class: "secondary-btn" },
        });
        /** @type {__VLS_StyleScopedClasses['secondary-btn']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "messages-container" },
            ref: "messagesContainer",
        });
        /** @type {__VLS_StyleScopedClasses['messages-container']} */ ;
        for (const [message, index] of __VLS_vFor((__VLS_ctx.currentMessages))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (index),
                ...{ class: (['message', { 'is-user': message.isUser }]) },
            });
            /** @type {__VLS_StyleScopedClasses['message']} */ ;
            /** @type {__VLS_StyleScopedClasses['is-user']} */ ;
            if (message.isUser) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "message-avatar user-avatar" },
                });
                /** @type {__VLS_StyleScopedClasses['message-avatar']} */ ;
                /** @type {__VLS_StyleScopedClasses['user-avatar']} */ ;
                (__VLS_ctx.username.charAt(0).toUpperCase());
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "message-content" },
                });
                /** @type {__VLS_StyleScopedClasses['message-content']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
                (message.content);
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "message-time" },
                });
                /** @type {__VLS_StyleScopedClasses['message-time']} */ ;
                (__VLS_ctx.username);
                (message.timestamp);
            }
            else {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: (['message-avatar', 'bot-avatar', __VLS_ctx.getAgentAvatarClass(message.agent)]) },
                });
                /** @type {__VLS_StyleScopedClasses['message-avatar']} */ ;
                /** @type {__VLS_StyleScopedClasses['bot-avatar']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
                (__VLS_ctx.getAgentAvatarText(message.agent));
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "message-content" },
                });
                /** @type {__VLS_StyleScopedClasses['message-content']} */ ;
                if (message.agentName) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "agent-name" },
                    });
                    /** @type {__VLS_StyleScopedClasses['agent-name']} */ ;
                    (message.agentName);
                }
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
                (message.content);
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "message-time" },
                });
                /** @type {__VLS_StyleScopedClasses['message-time']} */ ;
                (message.agentName || 'Bio-Agent');
                (message.timestamp);
            }
            // @ts-ignore
            [username, username, currentView, currentChatTitle, clearCurrentChat, currentMessages, getAgentAvatarClass, getAgentAvatarText,];
        }
        if (__VLS_ctx.loading) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "typing-indicator" },
            });
            /** @type {__VLS_StyleScopedClasses['typing-indicator']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "typing-dots" },
            });
            /** @type {__VLS_StyleScopedClasses['typing-dots']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
            ...{ onSubmit: (__VLS_ctx.handleSend) },
            ...{ class: "chat-input-form" },
        });
        /** @type {__VLS_StyleScopedClasses['chat-input-form']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "input-wrapper" },
        });
        /** @type {__VLS_StyleScopedClasses['input-wrapper']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
            ...{ onKeydown: (__VLS_ctx.handleSend) },
            value: (__VLS_ctx.inputMessage),
            placeholder: "输入您的问题...",
            rows: "2",
            disabled: (__VLS_ctx.loading),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ class: "send-btn" },
            type: "submit",
            disabled: (__VLS_ctx.loading || !__VLS_ctx.inputMessage.trim()),
        });
        /** @type {__VLS_StyleScopedClasses['send-btn']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
            viewBox: "0 0 24 24",
            width: "20",
            height: "20",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
            d: "M22 2L11 13l3 5H2l8-10 2 2v8z",
            stroke: "currentColor",
            'stroke-width': "2",
            fill: "none",
            'stroke-linecap': "round",
            'stroke-linejoin': "round",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
            ...{ class: "task-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['task-panel']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
            ...{ class: "task-panel-header" },
        });
        /** @type {__VLS_StyleScopedClasses['task-panel-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "task-count" },
        });
        /** @type {__VLS_StyleScopedClasses['task-count']} */ ;
        (__VLS_ctx.taskList.length);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "task-list" },
        });
        /** @type {__VLS_StyleScopedClasses['task-list']} */ ;
        for (const [task] of __VLS_vFor((__VLS_ctx.taskList))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (task.id),
                ...{ class: (['task-item', task.status]) },
            });
            /** @type {__VLS_StyleScopedClasses['task-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "task-header" },
            });
            /** @type {__VLS_StyleScopedClasses['task-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "task-step" },
            });
            /** @type {__VLS_StyleScopedClasses['task-step']} */ ;
            (task.step);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: (['task-status-badge', task.status]) },
            });
            /** @type {__VLS_StyleScopedClasses['task-status-badge']} */ ;
            (__VLS_ctx.getStatusText(task.status));
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
                ...{ class: "task-title" },
            });
            /** @type {__VLS_StyleScopedClasses['task-title']} */ ;
            (task.task_description);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "task-agent" },
            });
            /** @type {__VLS_StyleScopedClasses['task-agent']} */ ;
            (task.agent);
            if (task.result) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "task-result" },
                });
                /** @type {__VLS_StyleScopedClasses['task-result']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
                (task.result);
            }
            if (task.status === 'in_progress') {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "task-progress" },
                });
                /** @type {__VLS_StyleScopedClasses['task-progress']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "progress-bar" },
                });
                /** @type {__VLS_StyleScopedClasses['progress-bar']} */ ;
            }
            // @ts-ignore
            [loading, loading, loading, handleSend, handleSend, inputMessage, inputMessage, taskList, taskList, getStatusText,];
        }
        if (__VLS_ctx.taskList.length === 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "empty-task-list" },
            });
            /** @type {__VLS_StyleScopedClasses['empty-task-list']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
                viewBox: "0 0 24 24",
                width: "48",
                height: "48",
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
                d: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
                stroke: "currentColor",
                'stroke-width': "2",
                fill: "none",
                'stroke-linecap': "round",
                'stroke-linejoin': "round",
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "empty-hint" },
            });
            /** @type {__VLS_StyleScopedClasses['empty-hint']} */ ;
        }
    }
}
// @ts-ignore
[taskList,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
