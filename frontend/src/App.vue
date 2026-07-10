<template>
  <main class="app-shell" :class="{ expanded: isLoggedIn }">
    <div class="aurora" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </div>

    <!-- 登录状态：输入用户名 -->
    <div v-if="!isLoggedIn" class="layout layout-centered">
      <section class="panel panel-form panel-centered">
        <header class="panel-head">
          <div class="logo">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M12 2.5c-.7 0-1.4.2-2 .6L4.6 7C3.6 7.6 3 8.7 3 9.9v4.2c0 1.2.6 2.3 1.6 2.9l5.4 3.9c1.2.8 2.8.8 4 0l5.4-3.9c1-.7 1.6-1.7 1.6-2.9V9.9c0-1.2-.6-2.3-1.6-2.9L14 3.1a3.6 3.6 0 0 0-2-.6Z"
              />
            </svg>
          </div>
          <div>
            <h1>Bio-Agent</h1>
            <p>一阳生生物科技智能助手</p>
          </div>
        </header>

        <form class="form" @submit.prevent="handleLogin">
          <label class="field">
            <span>用户名</span>
            <input
              v-model="username"
              type="text"
              placeholder="请输入您的用户名"
              required
              autocomplete="username"
            />
          </label>

          <div class="form-actions">
            <button class="submit" type="submit" :disabled="loading">
              <span class="submit-label">
                <svg
                  v-if="loading"
                  class="spinner"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="9" stroke-width="3" />
                </svg>
                {{ loading ? "登录中..." : "进入系统" }}
              </span>
            </button>
          </div>
        </form>

        <p v-if="error" class="error-chip">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path
              d="M10 3.2c-.3 0-.6.2-.8.5L3.4 15c-.4.7.1 1.6.8 1.6h11.6c.7 0 1.2-.9.8-1.6L10.8 3.7c-.2-.3-.5-.5-.8-.5Zm0 4.3c.4 0 .7.3.7.7v4c0 .4-.3.7-.7.7s-.7-.3-.7-.7V8.2c0-.4.3-.7.7-.7Zm0 6.6a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"
            />
          </svg>
          {{ error }}
        </p>
      </section>
    </div>

    <!-- 登录后：主界面 -->
    <div v-else class="layout layout-fullscreen">
      <!-- 左侧：聊天列表和用户信息 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <div class="user-info">
            <div class="user-avatar">
              <span>{{ username.charAt(0).toUpperCase() }}</span>
            </div>
            <div>
              <h3>{{ username }}</h3>
              <p class="user-status">在线</p>
            </div>
          </div>
          <button class="logout-btn" @click="handleLogout">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path d="M17 7l-5 5 5 5M7 7h12v10H7V7z" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            退出
          </button>
        </div>

        <div class="sidebar-actions">
          <button class="new-chat-btn" @click="startNewChat">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
            </svg>
            新对话
          </button>
        </div>

        <!-- 对话历史列表 -->
        <div class="chat-history">
          <h4>最近对话</h4>
          <ul>
            <li
              v-for="(chat, index) in chatHistory"
              :key="index"
              :class="{ active: currentChatIndex === index }"
              @click="switchChat(index)"
            >
              <div class="chat-item-content">
                <div class="chat-preview">
                  <span class="chat-title">{{ chat.title }}</span>
                  <span class="chat-time">{{ chat.timestamp }}</span>
                </div>
                <p class="chat-last-message">{{ chat.lastMessage }}</p>
              </div>
              <button
                class="delete-chat-btn"
                @click.stop="deleteChat(index)"
                title="删除对话"
              >
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </li>
          </ul>
        </div>
      </aside>

      <AdminPanel v-if="currentView === 'admin'" />

      <template v-else>
      <!-- 中间：聊天内容 -->
      <section class="panel panel-chat">
        <header class="chat-header">
          <div class="chat-title-bar">
            <h2>{{ currentChatTitle }}</h2>
          </div>
          <div class="chat-controls">
            <button class="voice-btn" :class="voiceState" @click="toggleVoiceCall">
              <span class="voice-dot"></span>
              {{ voiceEnabled ? voiceStatus : '语音通话' }}
            </button>
            <button class="secondary-btn" @click="clearCurrentChat">
              清空对话
            </button>
          </div>
        </header>

        <!-- 消息列表 -->
        <div class="messages-container" ref="messagesContainer">
          <div
            v-for="(message, index) in currentMessages"
            :key="index"
            :class="['message', { 'is-user': message.isUser }]"
          >
            <!-- 用户消息 -->
            <template v-if="message.isUser">
              <div class="message-avatar user-avatar">
                {{ username.charAt(0).toUpperCase() }}
              </div>
              <div class="message-content">
                <p>{{ message.content }}</p>
                <span class="message-time">{{ username }} · {{ message.timestamp }}</span>
              </div>
            </template>
            
            <!-- Agent消息（群聊效果） -->
            <template v-else>
              <div :class="['message-avatar', 'bot-avatar', getAgentAvatarClass(message.agent)]">
                <span>{{ getAgentAvatarText(message.agent) }}</span>
              </div>
              <div class="message-content">
                <span v-if="message.agentName" class="agent-name">{{ message.agentName }}</span>
                <p>{{ message.content }}</p>
                <span class="message-time">{{ message.agentName || 'Bio-Agent' }} · {{ message.timestamp }}</span>
              </div>
            </template>
          </div>
          
          <!-- 加载中状态 -->
          <div v-if="loading" class="typing-indicator">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>Bio-Agent 正在思考...</span>
          </div>
        </div>

        <!-- 输入框 -->
        <form class="chat-input-form" @submit.prevent="handleSend">
          <div class="input-wrapper">
            <textarea
              v-model="inputMessage"
              placeholder="输入您的问题..."
              rows="2"
              :disabled="loading"
              @keydown.enter.exact.prevent="handleSend"
            ></textarea>
          </div>
          <button class="send-btn" type="submit" :disabled="loading || !inputMessage.trim()">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path d="M22 2L11 13l3 5H2l8-10 2 2v8z" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </form>
      </section>

      <!-- 右侧：任务清单面板 -->
      <aside class="task-panel">
        <header class="task-panel-header">
          <h3>任务清单</h3>
          <span class="task-count">{{ taskList.length }} 个任务</span>
        </header>
        
        <!-- 任务列表 -->
        <div class="task-list">
          <div
            v-for="task in taskList"
            :key="task.id"
            :class="['task-item', task.status]"
          >
            <div class="task-header">
              <span class="task-step">步骤 {{ task.step }}</span>
              <span :class="['task-status-badge', task.status]">
                {{ getStatusText(task.status) }}
              </span>
            </div>
            <h4 class="task-title">{{ task.task_description }}</h4>
            <p class="task-agent">执行Agent: {{ task.agent }}</p>
            <div v-if="task.result" class="task-result">
              <p>{{ task.result }}</p>
            </div>
            <div v-if="task.status === 'in_progress'" class="task-progress">
              <div class="progress-bar"></div>
            </div>
          </div>
          
          <div v-if="taskList.length === 0" class="empty-task-list">
            <svg viewBox="0 0 24 24" width="48" height="48">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <p>暂无任务</p>
            <p class="empty-hint">发送消息后，任务将显示在这里</p>
          </div>
        </div>
      </aside>
      </template>
    </div>
  </main>
</template>

<script lang="ts" setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from "vue";
import { getConversationHistory, getVoiceWsUrl, isVoiceWsSecure, runResearchStream, type ConversationRecord } from "./services/api";
import AdminPanel from "./components/AdminPanel.vue";

interface Message {
  content: string;
  isUser: boolean;
  timestamp: string;
  agent?: string;
  agentName?: string;
}

interface Chat {
  title: string;
  messages: Message[];
  lastMessage: string;
  timestamp: string;
}

interface TaskItem {
  id: number;
  step: number;
  agent: string;
  task_description: string;
  status: string;
  result?: string;
  dependency?: number;
}

// 登录状态
const isLoggedIn = ref(false);
const username = ref("");
const loading = ref(false);
const error = ref("");

// 聊天状态
const currentView = ref<"chat" | "admin">("chat");
const chatHistory = ref<Chat[]>([]);
const currentChatIndex = ref(-1);
const inputMessage = ref("");

// 任务清单
const taskList = ref<TaskItem[]>([]);

type VoiceState = "idle" | "listening" | "thinking" | "speaking" | "interrupted";
const voiceState = ref<VoiceState>("idle");
const voiceEnabled = ref(false);
const voiceStatus = computed(() => {
  const map: Record<VoiceState, string> = {
    idle: "语音通话",
    listening: "正在聆听",
    thinking: "正在理解",
    speaking: "正在播报",
    interrupted: "已打断"
  };
  return map[voiceState.value];
});
let voiceSocket: WebSocket | null = null;
let mediaRecorder: MediaRecorder | null = null;
let mediaStream: MediaStream | null = null;
let audioContext: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let vadTimer = 0;
let speechStartedAt = 0;
let lastSpeechAt = 0;
let recordingChunks: BlobPart[] = [];
let currentBotVoiceMessage: Message | null = null;
let currentAudio: HTMLAudioElement | null = null;
const audioQueue: Array<{ text: string; audio: string; format: string }> = [];
let playing = false;
let currentPlayedText = "";
let audioPlaybackUnlocked = false;
let speechStartSent = false;
let closingVoiceCall = false;
let speechCandidateSince = 0;

const vadThreshold = 0.015;
const vadStartDelay = 160;
const minRecordingMs = 600;
const minAudioBytes = 2000;


// 消息容器引用
const messagesContainer = ref<HTMLElement | null>(null);

// 计算当前对话
const currentChat = computed(() => {
  if (currentChatIndex.value >= 0 && currentChatIndex.value < chatHistory.value.length) {
    return chatHistory.value[currentChatIndex.value];
  }
  return null;
});

const currentMessages = computed(() => currentChat.value?.messages || []);

const currentChatTitle = computed(() => {
  if (!currentChat.value) return "新对话";
  return currentChat.value.title;
});

// 获取格式化时间
function getTimeString(): string {
  const now = new Date();
  return now.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function getDateString(): string {
  const now = new Date();
  return now.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

// 获取任务状态文本
function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    pending: "待执行",
    in_progress: "执行中",
    completed: "已完成",
    error: "出错"
  };
  return statusMap[status] || status;
}

// 获取Agent头像样式类
function getAgentAvatarClass(agent?: string): string {
  const agentClassMap: Record<string, string> = {
    'master_agent': 'agent-master',
    'knowledge_agent': 'agent-knowledge',
    'automation_agent': 'agent-automation'
  };
  return agentClassMap[agent || ''] || 'agent-default';
}

// 获取Agent头像显示文本
function getAgentAvatarText(agent?: string): string {
  const agentTextMap: Record<string, string> = {
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
    await loadChatHistory();
    
    isLoggedIn.value = true;
    
    if (chatHistory.value.length === 0) {
      startNewChat();
    }
    
    nextTick(() => {
      const textarea = document.querySelector("textarea") as HTMLTextAreaElement;
      if (textarea) textarea.focus();
    });
    
  } catch (err) {
    error.value = err instanceof Error ? err.message : "登录失败";
  } finally {
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
  const newChat: Chat = {
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
    const textarea = document.querySelector("textarea") as HTMLTextAreaElement;
    if (textarea) textarea.focus();
  });
}

// 切换对话
function switchChat(index: number) {
  currentView.value = "chat";
  currentChatIndex.value = index;
  inputMessage.value = "";
  taskList.value = [];

  nextTick(() => {
    const textarea = document.querySelector("textarea") as HTMLTextAreaElement;
    if (textarea) textarea.focus();
  });
}

// 删除对话
function deleteChat(index: number) {
  chatHistory.value.splice(index, 1);

  // 如果删除的是当前对话
  if (currentChatIndex.value === index) {
    if (chatHistory.value.length > 0) {
      // 切换到第一个对话
      currentChatIndex.value = 0;
    } else {
      // 没有对话了，创建一个新对话
      currentChatIndex.value = -1;
      startNewChat();
    }
  } else if (currentChatIndex.value > index) {
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

async function toggleVoiceCall() {
  if (voiceEnabled.value) {
    stopVoiceCall();
    return;
  }
  if (!currentChat.value) return;

  if (!isVoiceWsSecure() && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
    showVoiceError("手机浏览器要求 HTTPS 才能使用麦克风和语音通话。请用 HTTPS 地址访问。 ");
    return;
  }

  if (window.isSecureContext === false && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
    showVoiceError("手机浏览器要求 HTTPS 才能使用麦克风。请用 HTTPS 地址访问，或在本机 localhost 测试。 ");
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    showVoiceError("当前浏览器不支持麦克风，或页面不是 HTTPS。手机访问请使用 HTTPS 地址。 ");
    return;
  }

  await unlockAudioPlayback();
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  } catch (error) {
    showVoiceError(error instanceof Error && error.name === "NotAllowedError"
      ? "麦克风权限被拒绝，请在浏览器设置中允许麦克风。"
      : "无法打开麦克风。手机访问局域网 HTTP 地址时，浏览器通常会禁止语音通话，请改用 HTTPS。"
    );
    return;
  }
  audioContext = new AudioContext();
  await audioContext.resume();
  const source = audioContext.createMediaStreamSource(mediaStream);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);

  const sessionId = `${username.value}-${Date.now()}`;
  closingVoiceCall = false;
  voiceSocket = new WebSocket(getVoiceWsUrl(sessionId));
  voiceSocket.onmessage = (message) => handleVoiceEvent(JSON.parse(message.data));
  voiceSocket.onerror = () => handleVoiceSocketClosed();
  voiceSocket.onclose = () => handleVoiceSocketClosed();
  voiceEnabled.value = true;
  voiceState.value = "listening";
  startVadLoop();
}

function showVoiceError(message: string) {
  if (currentChat.value) {
    currentChat.value.messages.push({ content: message, isUser: false, timestamp: getTimeString(), agent: "voice_agent", agentName: "语音Agent" });
    nextTick(() => scrollToBottom());
  }
}

async function unlockAudioPlayback() {
  if (audioPlaybackUnlocked) return;
  const silentAudio = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=");
  silentAudio.muted = true;
  try {
    await silentAudio.play();
    silentAudio.pause();
    audioPlaybackUnlocked = true;
  } catch {
    audioPlaybackUnlocked = false;
  }
}

function getAudioMime(format: string): string {
  if (format === "mp3") return "audio/mpeg";
  if (format === "wav") return "audio/wav";
  if (format === "opus") return "audio/ogg; codecs=opus";
  return `audio/${format}`;
}

function getAudioSource(audio: string, format: string): string {
  if (audio.startsWith("data:audio/")) return audio;
  return `data:${getAudioMime(format)};base64,${audio.replace(/\s/g, "")}`;
}

function stopVoiceCall(sendInterrupt = true) {
  closingVoiceCall = true;
  voiceEnabled.value = false;
  voiceState.value = "idle";
  window.clearInterval(vadTimer);
  stopRecording(false);
  stopPlayback(true);
  mediaStream?.getTracks().forEach((track) => track.stop());
  mediaStream = null;
  audioContext?.close();
  audioContext = null;
  analyser = null;
  if (sendInterrupt && voiceSocket?.readyState === WebSocket.OPEN) {
    voiceSocket.send(JSON.stringify({ type: "interrupt" }));
  }
  voiceSocket?.close();
  voiceSocket = null;
  speechStartSent = false;
}

function handleVoiceSocketClosed() {
  if (closingVoiceCall) return;
  voiceState.value = "interrupted";
  window.clearInterval(vadTimer);
  stopRecording(false);
  stopPlayback(true);
  mediaStream?.getTracks().forEach((track) => track.stop());
  mediaStream = null;
  audioContext?.close();
  audioContext = null;
  analyser = null;
  voiceSocket = null;
  voiceEnabled.value = false;
  speechStartSent = false;
  if (currentChat.value) {
    currentChat.value.messages.push({ content: "语音连接已断开，请重新点击语音通话。", isUser: false, timestamp: getTimeString() });
  }
}

function startVadLoop() {
  const data = new Uint8Array(analyser?.frequencyBinCount || 0);
  vadTimer = window.setInterval(() => {
    if (!voiceEnabled.value || !analyser) return;
    analyser.getByteTimeDomainData(data);
    const rms = Math.sqrt(data.reduce((sum, value) => {
      const normalized = (value - 128) / 128;
      return sum + normalized * normalized;
    }, 0) / data.length);
    const speaking = rms > vadThreshold;
    const now = Date.now();

    if (speaking) {
      if (!speechCandidateSince) speechCandidateSince = now;
      lastSpeechAt = now;
    } else {
      speechCandidateSince = 0;
    }

    const stableSpeaking = speaking && now - speechCandidateSince >= vadStartDelay;
    if (stableSpeaking && (voiceState.value === "speaking" || voiceState.value === "thinking")) {
      interruptVoiceTurn();
    }
    if (stableSpeaking) {
      if (!speechStartSent) {
        sendSpeechStart();
        speechStartSent = true;
      }
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        startRecording();
        speechStartedAt = now;
      }
    }
    if (mediaRecorder?.state === "recording" && now - lastSpeechAt > 950 && now - speechStartedAt > minRecordingMs) {
      stopRecording(true);
    }
  }, 80);
}

function sendSpeechStart() {
  if (voiceSocket?.readyState !== WebSocket.OPEN) return;
  const history = currentMessages.value.map((msg) => ({ role: msg.isUser ? "user" : "assistant", content: msg.content }));
  voiceSocket.send(JSON.stringify({ type: "speech_start", history }));
}

function getSupportedRecordingType(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/aac"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function startRecording() {
  if (!mediaStream) return;
  recordingChunks = [];
  const mimeType = getSupportedRecordingType();
  mediaRecorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordingChunks.push(event.data);
  };
  mediaRecorder.onstop = () => sendRecordedAudio();
  mediaRecorder.start(120);
  voiceState.value = "listening";
}

function stopRecording(send: boolean) {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;
  if (!send) mediaRecorder.onstop = null;
  mediaRecorder.stop();
}

async function sendRecordedAudio() {
  if (!recordingChunks.length || voiceSocket?.readyState !== WebSocket.OPEN) return;
  const blob = new Blob(recordingChunks, { type: mediaRecorder?.mimeType || "audio/webm" });
  if (blob.size < minAudioBytes) {
    recordingChunks = [];
    speechStartSent = false;
    speechCandidateSince = 0;
    return;
  }
  const audio = await blobToBase64(blob);
  const history = currentMessages.value.map((msg) => ({ role: msg.isUser ? "user" : "assistant", content: msg.content }));
  voiceSocket.send(JSON.stringify({ type: "audio", audio, filename: "utterance.webm", history }));
  recordingChunks = [];
  speechStartSent = false;


  speechCandidateSince = 0;
  speechStartedAt = 0;
  lastSpeechAt = 0;

}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function interruptVoiceTurn() {
  voiceState.value = "interrupted";
  stopPlayback(true);
  if (voiceSocket?.readyState === WebSocket.OPEN) {
    voiceSocket.send(JSON.stringify({ type: "interrupt" }));
  }
}

function stopPlayback(clearQueue: boolean) {
  currentAudio?.pause();
  currentAudio = null;
  playing = false;
  if (clearQueue) audioQueue.splice(0);
}

function handleVoiceEvent(event: any) {
  if (event.type === "state") voiceState.value = event.state;
  if (event.type === "interrupted") voiceState.value = "interrupted";
  if (event.type === "asr_ignored") {
    voiceState.value = voiceEnabled.value ? "listening" : "idle";
    currentBotVoiceMessage = null;
    return;
  }
  if (event.type === "intent_preview" && event.text) {
    voiceState.value = "thinking";
  }
  if (event.type === "asr_final" && currentChat.value && event.text) {
    currentChat.value.messages.push({ content: event.text, isUser: true, timestamp: getTimeString() });
    currentChat.value.lastMessage = event.text.slice(0, 30);
    currentBotVoiceMessage = null;
  }
  if (event.type === "llm_chunk" && currentChat.value) {
    if (!currentBotVoiceMessage) {
      currentBotVoiceMessage = { content: "", isUser: false, timestamp: getTimeString(), agent: "voice_agent", agentName: "语音Agent" };
      currentChat.value.messages.push(currentBotVoiceMessage);
    }
    currentBotVoiceMessage.content += event.text || "";
    currentChat.value.lastMessage = currentBotVoiceMessage.content.slice(0, 30);
    nextTick(() => scrollToBottom());
  }
  if (event.type === "tts_chunk") {
    if (!event.audio && currentChat.value) {
      currentChat.value.messages.push({ content: "收到 TTS 事件，但音频数据为空。", isUser: false, timestamp: getTimeString() });
      return;
    }
    audioQueue.push({ text: event.text, audio: event.audio, format: event.format || "mp3" });
    playNextAudio();
  }
  if (event.type === "done") {
    voiceState.value = voiceEnabled.value ? "listening" : "idle";
    currentBotVoiceMessage = null;
  }
  if (event.type === "error" && currentChat.value) {
    currentChat.value.messages.push({ content: event.detail || "语音服务出错", isUser: false, timestamp: getTimeString() });
  }
}

function playNextAudio() {
  if (playing || audioQueue.length === 0) return;
  const item = audioQueue.shift()!;
  if (!item.audio) {
    playNextAudio();
    return;
  }
  playing = true;
  voiceState.value = "speaking";
  currentPlayedText = item.text;
  const audioUrl = getAudioSource(item.audio, item.format);
  currentAudio = new Audio(audioUrl);
  currentAudio.onended = () => {
    if (voiceSocket?.readyState === WebSocket.OPEN) {
      voiceSocket.send(JSON.stringify({ type: "played", text: currentPlayedText }));
    }
    playing = false;
    currentAudio = null;
    playNextAudio();
    if (!playing && audioQueue.length === 0 && voiceEnabled.value) voiceState.value = "listening";
  };
  currentAudio.onerror = () => {
    playing = false;
    currentAudio = null;
    if (currentChat.value) {
      currentChat.value.messages.push({ content: "音频播放失败，请检查浏览器自动播放权限或音频格式。", isUser: false, timestamp: getTimeString() });
    }
    playNextAudio();
  };
  currentAudio.play().catch((error) => {
    playing = false;
    currentAudio = null;
    if (currentChat.value) {
      currentChat.value.messages.push({ content: `音频播放被浏览器阻止：${error instanceof Error ? error.message : '未知错误'}`, isUser: false, timestamp: getTimeString() });
    }
  });
}

onBeforeUnmount(() => stopVoiceCall(false));

// 发送消息
async function handleSend() {
  if (!inputMessage.value.trim() || loading.value || !currentChat.value) {
    return;
  }

  const userMessage: Message = {
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
    const history = currentChat.value.messages.map((msg: Message) => ({
      role: msg.isUser ? 'user' : 'assistant',
      content: msg.content
    }));
    
    await runResearchStream(
      { username: username.value, topic: userMessage.content, history },
      (event) => {
        handleStreamEvent(event);
      }
    );
  } catch (err) {
    const errorMessage: Message = {
      content: err instanceof Error ? err.message : "发送消息失败，请重试",
      isUser: false,
      timestamp: getTimeString()
    };
    currentChat.value.messages.push(errorMessage);
    currentChat.value.lastMessage = "发送失败";
  } finally {
    loading.value = false;
    saveChatHistory();
    
    await nextTick();
    scrollToBottom();
  }
}

// 处理流式事件
function handleStreamEvent(event: any) {
  console.log("Stream event:", event);
  
  switch (event.type) {
    case "tasks":
      if (event.tasks && Array.isArray(event.tasks)) {
        taskList.value = event.tasks.map((task: any, index: number) => ({
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
      const botMessage: Message = {
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
            (currentMessage as any).isComplete) {
          // 创建新消息
          const newMessage: Message = {
            content: event.content || "",
            isUser: false,
            timestamp: getTimeString(),
            agent: agent || undefined,
            agentName: agentName || undefined
          } as any;
          (newMessage as any).isComplete = false;
          currentChat.value.messages.push(newMessage);
        } else {
          // 更新现有消息
          currentMessage.content += event.content || "";
        }
        
        // 标记完成
        if (event.complete) {
          (currentChat.value.messages.filter(m => !m.isUser).pop() as any).isComplete = true;
        }
        
        currentChat.value.lastMessage = currentChat.value.messages[currentChat.value.messages.length - 1].content.slice(0, 30) + "...";
        nextTick(() => scrollToBottom());
      }
      break;
      
    case "message":
      const message: Message = {
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
      const errorMsg: Message = {
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
  if (!username.value) return;
  
  const data = {
    username: username.value,
    chats: chatHistory.value
  };
  
  localStorage.setItem(`bioagent_${username.value}`, JSON.stringify(data));
}

function formatRecordDate(value?: string | null): string {
  if (!value) return getDateString();
  return new Date(value).toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

function historyToMessages(history: Array<{ role: string; content: string }>, createdAt?: string | null): Message[] {
  const timestamp = createdAt
    ? new Date(createdAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
    : getTimeString();
  return history
    .filter((item) => item.content)
    .map((item) => ({
      content: item.content,
      isUser: item.role === "user",
      timestamp
    }));
}

function recordToChat(record: ConversationRecord): Chat {
  const messages = Array.isArray(record.history_json) && record.history_json.length > 0
    ? historyToMessages(record.history_json, record.created_at)
    : [
        { content: record.request_text, isUser: true, timestamp: getTimeString() },
        ...(record.response_text ? [{ content: record.response_text, isUser: false, timestamp: getTimeString() }] : [])
      ];
  const lastMessage = messages[messages.length - 1]?.content || "";
  return {
    title: record.request_text.slice(0, 20) + (record.request_text.length > 20 ? "..." : ""),
    messages,
    lastMessage: lastMessage.slice(0, 30) + (lastMessage.length > 30 ? "..." : ""),
    timestamp: formatRecordDate(record.created_at)
  };
}

function mergeConversationRecords(records: ConversationRecord[]): Chat[] {
  const latestFullHistory = [...records]
    .reverse()
    .find((record) => Array.isArray(record.history_json) && record.history_json.length > 0);
  if (latestFullHistory) {
    return [recordToChat(latestFullHistory)];
  }
  return records.map(recordToChat).reverse();
}

// 加载聊天历史
async function loadChatHistory() {
  if (!username.value) return;

  const remoteHistory = await getConversationHistory(username.value.trim());
  if (remoteHistory.conversations.length > 0) {
    chatHistory.value = mergeConversationRecords(remoteHistory.conversations);
    currentChatIndex.value = 0;
    saveChatHistory();
    return;
  }
  
  const stored = localStorage.getItem(`bioagent_${username.value}`);
  if (stored) {
    try {
      const data = JSON.parse(stored);
      if (data.chats && Array.isArray(data.chats)) {
        chatHistory.value = data.chats;
        currentChatIndex.value = 0;
      }
    } catch (e) {
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
</script>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  padding: 72px 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(circle at 20% 20%, #f8fafc, #dbeafe 60%);
  color: #1f2937;
  overflow: hidden;
  box-sizing: border-box;
  transition: padding 0.4s ease;
}

.app-shell.expanded {
  padding: 0;
  align-items: stretch;
}

.aurora {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.55;
}

.aurora span {
  position: absolute;
  width: 45vw;
  height: 45vw;
  max-width: 520px;
  max-height: 520px;
  background: radial-gradient(circle, rgba(148, 197, 255, 0.35), transparent 60%);
  filter: blur(90px);
  animation: float 26s infinite linear;
}

.aurora span:nth-child(1) {
  top: -20%;
  left: -18%;
  animation-delay: 0s;
}

.aurora span:nth-child(2) {
  bottom: -25%;
  right: -20%;
  background: radial-gradient(circle, rgba(166, 139, 255, 0.28), transparent 60%);
  animation-delay: -9s;
}

.aurora span:nth-child(3) {
  top: 35%;
  left: 45%;
  background: radial-gradient(circle, rgba(164, 219, 216, 0.26), transparent 60%);
  animation-delay: -16s;
}

@keyframes float {
  0% { transform: translateX(0) translateY(0) rotate(0deg); }
  100% { transform: translateX(100px) translateY(50px) rotate(360deg); }
}

.layout {
  position: relative;
  width: 100%;
  display: flex;
  gap: 24px;
  z-index: 1;
  transition: all 0.4s ease;
}

.layout-centered {
  max-width: 600px;
  justify-content: center;
  align-items: center;
}

.layout-fullscreen {
  height: 100vh;
  max-width: 100%;
  gap: 0;
  align-items: stretch;
}

.panel {
  position: relative;
  flex: 1 1 360px;
  padding: 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(8px);
  overflow: hidden;
}

.panel-form {
  max-width: 420px;
}

.panel-centered {
  width: 100%;
  max-width: 600px;
  padding: 40px;
  box-shadow: 0 32px 64px rgba(15, 23, 42, 0.15);
  transform: scale(1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.panel-centered:hover {
  transform: scale(1.02);
  box-shadow: 0 40px 80px rgba(15, 23, 42, 0.2);
}

.panel-chat {
  min-width: 360px;
  flex: 2 1 420px;
  display: flex;
  flex-direction: column;
  padding: 0;
  border-radius: 0;
}

.panel::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(125, 86, 255, 0.1));
  opacity: 0;
  transition: opacity 0.35s ease;
  z-index: 0;
}

.panel:hover::before {
  opacity: 1;
}

.panel > * {
  position: relative;
  z-index: 1;
}

.panel-form h1 {
  margin: 0;
  font-size: 26px;
  letter-spacing: 0.01em;
  color: #1e293b;
}

.panel-form p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.logo {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.4);
}

.logo svg {
  width: 28px;
  height: 28px;
  fill: #f8fafc;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field span {
  font-weight: 600;
  color: #475569;
}

textarea,
input,
select {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.92);
  color: #1f2937;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
  font-family: inherit;
}

textarea:focus,
input:focus,
select:focus {
  outline: none;
  border-color: rgba(37, 99, 235, 0.65);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
  background: #ffffff;
}

textarea {
  resize: vertical;
  min-height: 60px;
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.submit {
  align-self: flex-start;
  padding: 12px 24px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  position: relative;
}

.submit-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.submit .spinner {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: rgba(255, 255, 255, 0.85);
  stroke-linecap: round;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.submit:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
}

.secondary-btn {
  padding: 10px 18px;
  border-radius: 14px;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.28);
  color: #1f2937;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.secondary-btn:hover {
  background: rgba(148, 163, 184, 0.2);
  border-color: rgba(148, 163, 184, 0.35);
  color: #0f172a;
}

.voice-btn {
  padding: 10px 16px;
  border-radius: 999px;
  border: 1px solid rgba(59, 130, 246, 0.28);
  background: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.voice-btn.speaking {
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}

.voice-btn.thinking {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.voice-btn.interrupted {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.voice-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.voice-btn.listening .voice-dot,
.voice-btn.speaking .voice-dot,
.voice-btn.thinking .voice-dot {
  animation: voicePulse 1s infinite ease-in-out;
}

@keyframes voicePulse {
  0%, 100% { transform: scale(0.85); opacity: 0.65; }
  50% { transform: scale(1.25); opacity: 1; }
}

.error-chip {
  margin-top: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 14px;
  color: #b91c1c;
  font-size: 14px;
}

.error-chip svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

/* 侧边栏样式 */
.sidebar {
  width: 280px;
  background: rgba(248, 250, 252, 0.98);
  border-right: 1px solid rgba(148, 163, 184, 0.2);
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  margin-bottom: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 16px;
}

.user-info h3 {
  margin: 0;
  font-size: 15px;
  color: #1e293b;
}

.user-status {
  margin: 2px 0 0;
  font-size: 12px;
  color: #10b981;
}

.logout-btn {
  padding: 8px 12px;
  border-radius: 12px;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.2);
  color: #dc2626;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.logout-btn:hover {
  background: rgba(248, 113, 113, 0.15);
  border-color: rgba(248, 113, 113, 0.3);
}

.sidebar-actions {
  margin-bottom: 16px;
}

.new-chat-btn {
  width: 100%;
  padding: 12px 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  border: none;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25);
}

.admin-btn {
  width: 100%;
  margin-top: 8px;
  padding: 11px 16px;
  border-radius: 14px;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.28);
  color: #1f2937;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.admin-btn.active,
.admin-btn:hover {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.3);
  color: #1d4ed8;
}

/* 聊天历史 */
.chat-history {
  flex: 1;
  overflow-y: auto;
}

.chat-history h4 {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.chat-history ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chat-history li {
  padding: 12px;
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.2s ease;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.chat-history li:hover {
  background: rgba(148, 163, 184, 0.1);
}

.chat-history li.active {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.3);
}

.chat-item-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.delete-chat-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease, background 0.2s ease, color 0.2s ease;
}

.chat-history li:hover .delete-chat-btn {
  opacity: 1;
}

.delete-chat-btn:hover {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.chat-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.chat-title {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.chat-time {
  font-size: 12px;
  color: #94a3b8;
}

.chat-last-message {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 聊天面板 */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.chat-title-bar h2 {
  margin: 0;
  font-size: 16px;
  color: #1e293b;
}

.chat-controls {
  display: flex;
  gap: 8px;
}

/* 消息容器 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 85%;
}

.message.is-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-avatar {
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.bot-avatar {
  background: rgba(148, 163, 184, 0.2);
  color: #64748b;
}

/* 主控调度专家 - 蓝色 */
.bot-avatar.agent-master {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
}

/* 知识问答专家 - 绿色 */
.bot-avatar.agent-knowledge {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

/* 自动化执行专家 - 橙色 */
.bot-avatar.agent-automation {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
}

/* 默认Agent */
.bot-avatar.agent-default {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: white;
}

.message-content {
  background: rgba(248, 250, 252, 0.9);
  padding: 12px 16px;
  border-radius: 18px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

.is-user .message-content {
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: white;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

.agent-name {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 4px;
}

.message-content p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.is-user .message-content p {
  color: white;
}

.message-time {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.is-user .message-time {
  color: rgba(255, 255, 255, 0.7);
}

/* 输入框 */
.chat-input-form {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.98);
}

.input-wrapper {
  flex: 1;
}

.chat-input-form textarea {
  width: 100%;
  box-sizing: border-box;
  border-radius: 16px;
  resize: none;
  min-height: 48px;
}

.send-btn {
  padding: 12px 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  border: none;
  color: white;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.25);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(248, 250, 252, 0.9);
  border-radius: 18px;
  width: fit-content;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.typing-indicator span:last-child {
  font-size: 14px;
  color: #64748b;
}

/* 任务清单面板 */
.task-panel {
  width: 320px;
  background: rgba(248, 250, 252, 0.98);
  border-left: 1px solid rgba(148, 163, 184, 0.2);
  display: flex;
  flex-direction: column;
}

.task-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.task-panel-header h3 {
  margin: 0;
  font-size: 15px;
  color: #1e293b;
}

.task-count {
  font-size: 13px;
  color: #64748b;
  background: rgba(148, 163, 184, 0.15);
  padding: 4px 10px;
  border-radius: 12px;
}

.task-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item {
  background: white;
  border-radius: 14px;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  transition: all 0.2s ease;
}

.task-item:hover {
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

.task-item.pending {
  border-left: 3px solid #94a3b8;
}

.task-item.in_progress {
  border-left: 3px solid #f59e0b;
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.05), white);
}

.task-item.completed {
  border-left: 3px solid #10b981;
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.05), white);
}

.task-item.error {
  border-left: 3px solid #ef4444;
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.05), white);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-step {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.task-status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 500;
}

.task-status-badge.pending {
  background: rgba(148, 163, 184, 0.15);
  color: #64748b;
}

.task-status-badge.in_progress {
  background: rgba(245, 158, 11, 0.15);
  color: #d97706;
}

.task-status-badge.completed {
  background: rgba(16, 185, 129, 0.15);
  color: #059669;
}

.task-status-badge.error {
  background: rgba(239, 68, 68, 0.15);
  color: #dc2626;
}

.task-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
}

.task-agent {
  margin: 0 0 10px;
  font-size: 12px;
  color: #94a3b8;
}

.task-result {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.15);
}

.task-result p {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.4;
}

.task-progress {
  margin-top: 10px;
  height: 4px;
  background: rgba(245, 158, 11, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, #f59e0b, #d97706);
  border-radius: 2px;
  animation: progressMove 1.5s ease-in-out infinite;
}

@keyframes progressMove {
  0% { width: 0%; }
  50% { width: 70%; }
  100% { width: 0%; }
}

.empty-task-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #94a3b8;
}

.empty-task-list svg {
  margin-bottom: 16px;
  color: #cbd5e1;
}

.empty-task-list p {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 500;
}

.empty-hint {
  font-size: 12px !important;
  color: #94a3b8 !important;
}

/* 滚动条样式 */
.messages-container::-webkit-scrollbar,
.chat-history::-webkit-scrollbar,
.task-list::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track,
.chat-history::-webkit-scrollbar-track,
.task-list::-webkit-scrollbar-track {
  background: rgba(226, 232, 240, 0.6);
  border-radius: 999px;
}

.messages-container::-webkit-scrollbar-thumb,
.chat-history::-webkit-scrollbar-thumb,
.task-list::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(129, 140, 248, 0.8), rgba(59, 130, 246, 0.7));
  border-radius: 999px;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .task-panel {
    display: none;
  }
}

@media (max-width: 768px) {
  .app-shell,
  .app-shell.expanded {
    min-height: 100dvh;
    padding: 0;
    overflow: hidden;
  }

  .aurora {
    display: none;
  }

  .layout-fullscreen {
    height: 100dvh;
    flex-direction: column;
    overflow: hidden;
  }

  .sidebar {
    width: 100%;
    max-height: 148px;
    padding: 10px 12px;
    border-right: none;
    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
    box-sizing: border-box;
    flex-shrink: 0;
  }

  .sidebar-header {
    padding-bottom: 8px;
    margin-bottom: 8px;
  }

  .user-avatar,
  .message-avatar {
    width: 32px;
    height: 32px;
    font-size: 13px;
  }

  .user-info h3 {
    font-size: 14px;
  }

  .user-status,
  .chat-history h4,
  .chat-last-message,
  .delete-chat-btn {
    display: none;
  }

  .sidebar-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }

  .new-chat-btn,
  .admin-btn {
    margin: 0;
    padding: 9px 10px;
    font-size: 13px;
  }

  .chat-history {
    flex: none;
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 2px;
  }

  .chat-history ul {
    flex-direction: row;
    gap: 6px;
  }

  .chat-history li {
    min-width: 112px;
    max-width: 150px;
    padding: 8px 10px;
    flex-shrink: 0;
  }

  .chat-preview {
    margin: 0;
    gap: 8px;
  }

  .chat-title {
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-time {
    display: none;
  }

  .panel-chat {
    min-width: 0;
    flex: 1;
    height: calc(100dvh - 148px);
  }

  .chat-header {
    padding: 10px 12px;
    align-items: flex-start;
    gap: 8px;
    flex-direction: column;
  }

  .chat-title-bar h2 {
    font-size: 15px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-controls {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
  }

  .voice-btn,
  .secondary-btn {
    min-height: 40px;
    padding: 9px 12px;
    justify-content: center;
    font-size: 13px;
  }

  .messages-container {
    padding: 12px;
    gap: 14px;
  }

  .message {
    max-width: 94%;
    gap: 8px;
  }

  .message-content {
    padding: 10px 12px;
    border-radius: 14px;
  }

  .message-content p {
    font-size: 14px;
    line-height: 1.45;
  }

  .message-time {
    font-size: 11px;
  }

  .chat-input-form {
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
    gap: 8px;
  }

  .chat-input-form textarea {
    min-height: 42px;
    max-height: 96px;
    padding: 11px 12px;
    font-size: 16px;
  }

  .send-btn {
    min-width: 46px;
    height: 46px;
    padding: 0 13px;
    border-radius: 14px;
  }

  .panel-centered {
    max-width: calc(100vw - 32px);
    padding: 28px 20px;
  }
}

@media (max-width: 420px) {
  .sidebar {
    max-height: 136px;
  }

  .panel-chat {
    height: calc(100dvh - 136px);
  }

  .logout-btn {
    padding: 7px 9px;
    font-size: 12px;
  }

  .voice-btn,
  .secondary-btn {
    font-size: 12px;
  }
}
</style>
