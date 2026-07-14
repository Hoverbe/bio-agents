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
            <img :src="agentProfileImage" alt="Bio-Agent avatar" />
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
      <section v-if="mobileCallVisible" class="mobile-call-screen">
        <div class="mobile-call-bg" aria-hidden="true"></div>
        <button class="mobile-call-back" type="button" aria-label="Back to chat" @click="closeMobileCall">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>

        <div class="mobile-call-body">
          <div class="mobile-call-hero">
            <div class="mobile-wave mobile-wave-left" aria-hidden="true">
              <span v-for="bar in 16" :key="`left-${bar}`"></span>
            </div>
            <img class="mobile-call-avatar" :src="agentProfileImage" alt="Bio-Agent avatar" />
            <div class="mobile-wave mobile-wave-right" aria-hidden="true">
              <span v-for="bar in 16" :key="`right-${bar}`"></span>
            </div>
          </div>

          <h2 class="mobile-call-name">一阳生-BioAgent</h2>
          <div class="mobile-call-state">✧ {{ mobileVoiceStatus }} ✧</div>
          <div class="mobile-call-time">{{ voiceElapsedLabel }}</div>

          <div class="mobile-live-title">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 10v4M9 7v10M13 4v16M17 8v8M21 11v2" />
            </svg>
            <span>实时字幕 · live transcript</span>
          </div>
          <p class="mobile-live-text">{{ mobileTranscript }}</p>
        </div>

        <div class="mobile-call-controls">
          <button class="mobile-call-tool" :class="{ active: mobileMuted }" type="button" @click="mobileMuted = !mobileMuted">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 3v8a4 4 0 0 1-8 0V3M8 19v3M5 22h6M16 9l5 5M21 9l-5 5" />
            </svg>
            <span>静音</span>
          </button>
          <button class="mobile-call-tool" :class="{ active: mobilePrivate }" type="button" @click="mobilePrivate = !mobilePrivate">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v10H6zM12 15v2" />
            </svg>
            <span>私密模式</span>
          </button>
          <button class="mobile-call-tool" :class="{ active: mobileSpeaker }" type="button" @click="mobileSpeaker = !mobileSpeaker">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 9v6h4l5 4V5L9 9H5zM17 9a4 4 0 0 1 0 6M19.5 6.5a8 8 0 0 1 0 11" />
            </svg>
            <span>扬声器</span>
          </button>
        </div>

        <button class="mobile-end-call" type="button" aria-label="End call" @click="closeMobileCall">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6.6 10.8c3.5-2.4 7.3-2.4 10.8 0l-2.1 2.1c-.4.4-1 .5-1.5.3a5.6 5.6 0 0 0-3.6 0c-.5.2-1.1.1-1.5-.3l-2.1-2.1z" />
          </svg>
        </button>
      </section>
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
      <section
        :class="['panel', 'panel-chat', { 'is-dragging-file': isAttachmentDragActive }]"
        @dragenter.prevent="handleAttachmentDragEnter"
        @dragover.prevent="handleAttachmentDragOver"
        @dragleave.prevent="handleAttachmentDragLeave"
        @drop.prevent="handleAttachmentDrop"
      >
        <div v-if="isAttachmentDragActive" class="attachment-drop-overlay">
          <div class="attachment-drop-panel">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 3v12m0-12 4 4m-4-4-4 4M5 15v3a3 3 0 0 0 3 3h8a3 3 0 0 0 3-3v-3" />
            </svg>
            <span>松开以上传附件</span>
          </div>
        </div>
        <header class="mobile-chat-topbar">
          <button class="mobile-icon-btn" type="button" aria-label="Back" @click="handleLogout">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M15 5l-7 7 7 7" />
            </svg>
          </button>
          <div class="mobile-chat-person">
            <h2>一阳生-BioAgent</h2>
            <span>online</span>
          </div>
          <div class="mobile-chat-actions">
            <button class="mobile-icon-btn" type="button" aria-label="Video call">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 7h9a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2zM17 11l4-3v8l-4-3" />
              </svg>
            </button>
            <button class="mobile-icon-btn" type="button" aria-label="Call" @click="openMobileCall">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6.6 3.8l3 3-2 2c1.1 2.3 2.9 4.1 5.2 5.2l2-2 3 3c.3.3.4.8.2 1.2-.8 1.8-2.5 3-4.5 3C8.4 19.2 4.8 15.6 4.8 10.5c0-2 .9-3.7 2.6-4.5.4-.2.9-.1 1.2.2z" />
              </svg>
            </button>
            <button class="mobile-icon-btn" type="button" aria-label="More" @click="mobileMenuOpen = !mobileMenuOpen">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 6h.01M12 12h.01M12 18h.01" />
              </svg>
            </button>
          </div>

          <div v-if="mobileMenuOpen" class="mobile-menu-panel">
            <button type="button" class="mobile-menu-action" @click="handleMobileNewChat">新对话</button>
            <div class="mobile-menu-title">历史对话</div>
            <button
              v-for="(chat, index) in chatHistory"
              :key="`mobile-history-${index}`"
              type="button"
              class="mobile-history-item"
              :class="{ active: currentChatIndex === index }"
              @click="handleMobileSwitchChat(index)"
            >
              <span>{{ chat.title }}</span>
              <small>{{ chat.timestamp }}</small>
            </button>
          </div>
        </header>
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
                <img class="mobile-bot-avatar-image" :src="agentProfileImage" alt="" />
                <span>{{ getAgentAvatarText(message.agent) }}</span>
              </div>
              <div class="message-content">
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
          <input
            ref="fileInput"
            class="attachment-input"
            type="file"
            accept=".pdf,.txt,.md,.markdown,.doc,.docx,.xls,.xlsx,.csv,.json,.fasta,.fa,.gb,.genbank"
            @change="handleAttachmentChange"
          />
          <button
            :class="['mobile-compose-tool', { 'is-active': selectedAttachment }]"
            type="button"
            aria-label="上传附件"
            :disabled="loading || attachmentStatus === 'uploading'"
            @click="openFilePicker"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M21 11.5l-8.5 8.5a5 5 0 0 1-7.1-7.1l9-9a3.5 3.5 0 0 1 5 5l-9 9a2 2 0 0 1-2.8-2.8l8.5-8.5" />
            </svg>
          </button>
          <div class="composer-main">
            <div v-if="selectedAttachment || attachmentStatus === 'uploading'" class="attachment-chip">
              <span class="attachment-dot"></span>
              <span class="attachment-name">{{ selectedAttachment?.filename || "附件解析中" }}</span>
              <span class="attachment-meta">{{ attachmentStatusText }}</span>
              <button type="button" class="attachment-remove" aria-label="移除附件" @click="removeAttachment">
                ×
              </button>
            </div>
            <p v-if="attachmentError" class="attachment-error">{{ attachmentError }}</p>
            <div class="input-wrapper">
              <textarea
                ref="messageInput"
                v-model="inputMessage"
                :placeholder="chatInputPlaceholder"
                rows="2"
                :disabled="loading"
                @keydown.enter.exact.prevent="handleSend"
              ></textarea>
              <div v-if="emojiPickerOpen" class="emoji-picker" role="menu" aria-label="Emoji">
                <button
                  v-for="emoji in emojiList"
                  :key="emoji"
                  type="button"
                  class="emoji-option"
                  @click="insertEmoji(emoji)"
                >
                  {{ emoji }}
                </button>
              </div>
            </div>
          </div>
          <button
            :class="['mobile-compose-tool', { 'is-active': emojiPickerOpen }]"
            type="button"
            aria-label="Emoji"
            :disabled="loading"
            @click="toggleEmojiPicker"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8.5 10h.01M15.5 10h.01M8 14c1.1 1.3 2.4 2 4 2s2.9-.7 4-2" />
            </svg>
          </button>
          <button class="send-btn" type="submit" :disabled="loading || attachmentStatus === 'uploading' || !canSend">
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
import { ref, computed, nextTick, watch, onBeforeUnmount, onMounted } from "vue";
import {
  getConversationHistory,
  getVoiceWsUrl,
  isVoiceWsSecure,
  parseAttachmentFile,
  runResearchStream,
  type ConversationRecord,
  type ParsedAttachment
} from "./services/api";
import AdminPanel from "./components/AdminPanel.vue";
import agentProfileImage from "./assets/bio-agent-profile-chun.png";

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
const fileInput = ref<HTMLInputElement | null>(null);
const messageInput = ref<HTMLTextAreaElement | null>(null);
const selectedAttachment = ref<ParsedAttachment | null>(null);
const attachmentStatus = ref<"idle" | "uploading" | "ready" | "error">("idle");
const attachmentError = ref("");
const isAttachmentDragActive = ref(false);
const emojiPickerOpen = ref(false);
const isMobileViewport = ref(false);
const mobileMenuOpen = ref(false);
const mobileCallVisible = ref(false);
const mobileMuted = ref(false);
const mobilePrivate = ref(false);
const mobileSpeaker = ref(true);
const voiceElapsedSeconds = ref(0);
let voiceElapsedTimer = 0;

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
let attachmentDragDepth = 0;

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

const emojiList = [
  "😀", "😄", "😊", "😂", "😍", "🥰", "😎", "🤔",
  "👍", "👏", "🙏", "💪", "🔥", "✨", "🎉", "✅",
  "❤️", "💡", "📎", "🧬", "🔬", "🧪", "📊", "📝"
];

const attachmentStatusText = computed(() => {
  if (attachmentStatus.value === "uploading") return "解析中";
  if (attachmentStatus.value === "ready" && selectedAttachment.value) {
    const sizeText = formatBytes(selectedAttachment.value.size || 0);
    return selectedAttachment.value.truncated ? `${sizeText} · 已截断` : sizeText;
  }
  if (attachmentStatus.value === "error") return "解析失败";
  return "";
});

const canSend = computed(() => {
  const hasMessage = inputMessage.value.trim().length > 0;
  const hasReadyAttachment = attachmentStatus.value === "ready" && !!selectedAttachment.value;
  return hasMessage || hasReadyAttachment;
});

const currentChatTitle = computed(() => {
  if (!currentChat.value) return "新对话";
  return currentChat.value.title;
});

const chatInputPlaceholder = computed(() => isMobileViewport.value ? "Write a letter..." : "输入您的问题...");

const mobileVoiceStatus = computed(() => {
  const map: Record<VoiceState, string> = {
    idle: "calling",
    listening: "listening",
    thinking: "thinking",
    speaking: "speaking",
    interrupted: "interrupted"
  };
  return map[voiceState.value];
});

const voiceElapsedLabel = computed(() => {
  const minutes = Math.floor(voiceElapsedSeconds.value / 60).toString().padStart(2, "0");
  const seconds = (voiceElapsedSeconds.value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
});

const mobileTranscript = computed(() => {
  const lastAssistant = [...currentMessages.value].reverse().find((message) => !message.isUser);
  return currentBotVoiceMessage?.content || lastAssistant?.content || "等待你开始说话";
});

function formatBytes(bytes: number): string {
  if (!bytes) return "已解析";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function openFilePicker() {
  attachmentError.value = "";
  fileInput.value?.click();
}

async function handleAttachmentChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  await uploadAttachmentFile(file);
  input.value = "";
}

async function uploadAttachmentFile(file: File) {
  if (loading.value || attachmentStatus.value === "uploading") return;

  attachmentStatus.value = "uploading";
  attachmentError.value = "";
  emojiPickerOpen.value = false;
  selectedAttachment.value = {
    filename: file.name,
    content: "",
    content_type: file.type || null,
    size: file.size,
    chars: 0,
    truncated: false
  };

  try {
    selectedAttachment.value = await parseAttachmentFile(file);
    attachmentStatus.value = "ready";
  } catch (err) {
    selectedAttachment.value = null;
    attachmentStatus.value = "error";
    attachmentError.value = err instanceof Error ? err.message : "附件解析失败";
  }
}

function eventHasFiles(event: DragEvent): boolean {
  return Array.from(event.dataTransfer?.types || []).includes("Files");
}

function handleAttachmentDragEnter(event: DragEvent) {
  if (!eventHasFiles(event) || loading.value) return;
  attachmentDragDepth += 1;
  isAttachmentDragActive.value = true;
}

function handleAttachmentDragOver(event: DragEvent) {
  if (!eventHasFiles(event) || loading.value) return;
  if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
  isAttachmentDragActive.value = true;
}

function handleAttachmentDragLeave(event: DragEvent) {
  if (!eventHasFiles(event)) return;
  attachmentDragDepth = Math.max(attachmentDragDepth - 1, 0);
  if (attachmentDragDepth === 0) {
    isAttachmentDragActive.value = false;
  }
}

async function handleAttachmentDrop(event: DragEvent) {
  attachmentDragDepth = 0;
  isAttachmentDragActive.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (!file || loading.value || attachmentStatus.value === "uploading") return;
  await uploadAttachmentFile(file);
}

function removeAttachment() {
  selectedAttachment.value = null;
  attachmentStatus.value = "idle";
  attachmentError.value = "";
  if (fileInput.value) fileInput.value.value = "";
}

function toggleEmojiPicker() {
  emojiPickerOpen.value = !emojiPickerOpen.value;
}

function insertEmoji(emoji: string) {
  const textarea = messageInput.value;
  const start = textarea?.selectionStart ?? inputMessage.value.length;
  const end = textarea?.selectionEnd ?? inputMessage.value.length;
  inputMessage.value = `${inputMessage.value.slice(0, start)}${emoji}${inputMessage.value.slice(end)}`;
  emojiPickerOpen.value = false;

  nextTick(() => {
    messageInput.value?.focus();
    const caret = start + emoji.length;
    messageInput.value?.setSelectionRange(caret, caret);
  });
}

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
  inputMessage.value = "";
  removeAttachment();
  emojiPickerOpen.value = false;
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
  removeAttachment();
  emojiPickerOpen.value = false;
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
  removeAttachment();
  emojiPickerOpen.value = false;
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

function updateViewportMode() {
  isMobileViewport.value = window.matchMedia("(max-width: 768px)").matches;
  if (!isMobileViewport.value) {
    mobileMenuOpen.value = false;
    mobileCallVisible.value = false;
    stopMobileCallTimer();
  }
}

function handleMobileNewChat() {
  mobileMenuOpen.value = false;
  startNewChat();
}

function handleMobileSwitchChat(index: number) {
  mobileMenuOpen.value = false;
  switchChat(index);
}

function startMobileCallTimer() {
  window.clearInterval(voiceElapsedTimer);
  voiceElapsedSeconds.value = 0;
  voiceElapsedTimer = window.setInterval(() => {
    voiceElapsedSeconds.value += 1;
  }, 1000);
}

function stopMobileCallTimer() {
  window.clearInterval(voiceElapsedTimer);
  voiceElapsedTimer = 0;
}

async function openMobileCall() {
  mobileMenuOpen.value = false;
  mobileCallVisible.value = true;
  startMobileCallTimer();
  if (!voiceEnabled.value) {
    await toggleVoiceCall();
  }
}

function closeMobileCall() {
  mobileCallVisible.value = false;
  stopMobileCallTimer();
  if (voiceEnabled.value) {
    stopVoiceCall();
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
  voiceSocket.onopen = () => showVoiceNotice("语音连接已建立，请开始说话。");
  voiceSocket.onmessage = (message) => handleVoiceEvent(JSON.parse(message.data));
  voiceSocket.onerror = () => handleVoiceSocketClosed();
  voiceSocket.onclose = () => handleVoiceSocketClosed();
  voiceEnabled.value = true;
  voiceState.value = "listening";
  startVadLoop();
}

function showVoiceNotice(message: string) {
  if (currentChat.value) {
    currentChat.value.messages.push({ content: message, isUser: false, timestamp: getTimeString(), agent: "voice_agent", agentName: "语音Agent" });
    nextTick(() => scrollToBottom());
  }
}

function showVoiceError(message: string) {
  showVoiceNotice(message);
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
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        startRecording();
        speechStartedAt = now;
      }
    } else {
      speechCandidateSince = 0;
    }

    const stableSpeaking = speaking && now - speechCandidateSince >= vadStartDelay;
    if (stableSpeaking && (voiceState.value === "speaking" || voiceState.value === "thinking")) {
      interruptVoiceTurn();
    }
    if (stableSpeaking && !speechStartSent && sendSpeechStart()) {
      speechStartSent = true;
    }
    if (mediaRecorder?.state === "recording" && now - lastSpeechAt > 950 && now - speechStartedAt > minRecordingMs) {
      stopRecording(true);
    }
  }, 80);
}

function sendSpeechStart(): boolean {
  if (voiceSocket?.readyState !== WebSocket.OPEN) return false;
  const history = currentMessages.value.map((msg) => ({ role: msg.isUser ? "user" : "assistant", content: msg.content }));
  voiceSocket.send(JSON.stringify({ type: "speech_start", history }));
  return true;
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
  if (!recordingChunks.length) {
    speechStartSent = false;
    speechCandidateSince = 0;
    return;
  }
  if (voiceSocket?.readyState !== WebSocket.OPEN) {
    showVoiceNotice("已检测到语音，但语音连接尚未就绪，请稍后再说一次。");
    recordingChunks = [];
    speechStartSent = false;
    speechCandidateSince = 0;
    return;
  }
  const blob = new Blob(recordingChunks, { type: mediaRecorder?.mimeType || "audio/webm" });
  if (blob.size < minAudioBytes) {
    showVoiceNotice(`已检测到语音，但录音太短或音量太低（${blob.size} 字节），请靠近麦克风再说一次。`);
    recordingChunks = [];
    speechStartSent = false;
    speechCandidateSince = 0;
    speechStartedAt = 0;
    lastSpeechAt = 0;
    return;
  }
  voiceState.value = "thinking";
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
  if (event.type === "prewarmed") voiceState.value = "listening";
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

onMounted(() => {
  updateViewportMode();
  window.addEventListener("resize", updateViewportMode);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", updateViewportMode);
  stopMobileCallTimer();
  stopVoiceCall(false);
});

// 发送消息
async function handleSend() {
  if (!canSend.value || loading.value || attachmentStatus.value === "uploading" || !currentChat.value) {
    return;
  }

  const text = inputMessage.value.trim() || "请根据附件内容进行分析。";
  const attachment = selectedAttachment.value;
  const displayContent = attachment
    ? `${text}\n\n附件：${attachment.filename}${attachment.truncated ? "（内容已截断）" : ""}`
    : text;

  const userMessage: Message = {
    content: displayContent,
    isUser: true,
    timestamp: getTimeString()
  };

  currentChat.value.messages.push(userMessage);
  
  if (currentChat.value.messages.length === 1) {
    currentChat.value.title = text.slice(0, 20) + (text.length > 20 ? "..." : "");
  }
  currentChat.value.lastMessage = displayContent.slice(0, 30) + (displayContent.length > 30 ? "..." : "");
  currentChat.value.timestamp = getDateString();

  inputMessage.value = "";
  emojiPickerOpen.value = false;
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
      {
        username: username.value,
        topic: text,
        history,
        attachments: attachment
          ? [{
              filename: attachment.filename,
              content: attachment.content,
              content_type: attachment.content_type,
              truncated: attachment.truncated
            }]
          : undefined
      },
      (event) => {
        handleStreamEvent(event);
      }
    );
    if (attachment) removeAttachment();
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

.panel-chat.is-dragging-file {
  outline: 2px solid rgba(37, 99, 235, 0.32);
  outline-offset: -2px;
}

.attachment-drop-overlay {
  position: absolute;
  inset: 0;
  z-index: 9;
  display: grid;
  place-items: center;
  pointer-events: none;
  background: rgba(248, 250, 252, 0.72);
  backdrop-filter: blur(6px);
}

.attachment-drop-panel {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  color: #1d4ed8;
  font-size: 15px;
  font-weight: 600;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
}

.attachment-drop-panel svg {
  width: 24px;
  height: 24px;
}

.attachment-drop-panel svg path {
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
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
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
}

.logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
  background: linear-gradient(135deg, #2563eb, #680b0b);
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
  background: linear-gradient(135deg, #2563eb, #bc0d3f);
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
  background: linear-gradient(135deg, #2563eb, #ca0970);
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
  gap: 14px;
  max-width: 78%;
  align-items: flex-end;
}

.message.is-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-avatar {
  background: linear-gradient(135deg, #2563eb, #9066da);
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.bot-avatar {
  overflow: hidden;
  background: #ffffff;
  color: #64748b;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
}

/* 主控调度专家 - 蓝色 */
.bot-avatar.agent-master {
  background: #ffffff;
  color: #64748b;
}

/* 知识问答专家 - 绿色 */
.bot-avatar.agent-knowledge {
  background: #ffffff;
  color: #64748b;
}

/* 自动化执行专家 - 橙色 */
.bot-avatar.agent-automation {
  background: #ffffff;
  color: #64748b;
}

/* 默认Agent */
.bot-avatar.agent-default {
  background: #ffffff;
  color: #64748b;
}

.bot-avatar > span {
  display: none;
}

.mobile-bot-avatar-image {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.message-content {
  background: rgba(248, 250, 252, 0.92);
  padding: 14px 17px;
  border-radius: 4px 18px 18px 18px;
  box-shadow: 0 8px 26px rgba(15, 23, 42, 0.06);
}

.is-user .message-content {
  background: rgba(226, 234, 246, 0.95);
  color: #304052;
  border-radius: 18px 18px 4px 18px;
  box-shadow: 0 8px 24px rgba(89, 116, 154, 0.12);
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
  font-size: 15px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.is-user .message-content p {
  color: inherit;
}

.message-time {
  display: block;
  margin-top: 9px;
  font-size: 12px;
  color: #8b96a5;
}

.is-user .message-time {
  color: #8b96a5;
}

/* 输入框 */
.chat-input-form {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 14px 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.96);
}

.attachment-input {
  display: none;
}

.composer-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-wrapper {
  position: relative;
  flex: 1;
  min-width: 0;
}

.attachment-chip {
  width: fit-content;
  max-width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 9px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 8px;
  background: rgba(239, 246, 255, 0.92);
  color: #334155;
  font-size: 12px;
  line-height: 1.2;
}

.attachment-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #2563eb;
  flex: 0 0 auto;
}

.attachment-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-meta {
  color: #64748b;
  flex: 0 0 auto;
}

.attachment-remove {
  width: 22px;
  height: 22px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.08);
  color: #475569;
  cursor: pointer;
  line-height: 1;
}

.attachment-error {
  margin: 0;
  color: #dc2626;
  font-size: 12px;
}

.chat-input-form textarea {
  width: 100%;
  box-sizing: border-box;
  border-radius: 999px;
  resize: none;
  min-height: 54px;
  max-height: 112px;
  padding: 15px 16px;
  background: rgba(248, 250, 252, 0.92);
  box-shadow: 0 10px 30px rgba(45, 57, 78, 0.06);
}

.mobile-compose-tool {
  width: 44px;
  height: 44px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  color: #6b7785;
  background: transparent;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  cursor: pointer;
}

.mobile-compose-tool.is-active {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
}

.mobile-compose-tool:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.emoji-picker {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  z-index: 8;
  width: 288px;
  max-width: calc(100vw - 32px);
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.14);
}

.emoji-option {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  font-size: 19px;
  line-height: 1;
  cursor: pointer;
}

.emoji-option:hover {
  background: rgba(226, 232, 240, 0.8);
}

.mobile-compose-tool svg {
  width: 25px;
  height: 25px;
}

.mobile-compose-tool svg path {
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.send-btn {
  width: 54px;
  height: 54px;
  min-width: 54px;
  padding: 0;
  border-radius: 50%;
  background: #26384d;
  border: none;
  color: white;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  box-shadow: 0 12px 28px rgba(38, 56, 77, 0.18);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(38, 56, 77, 0.24);
}

.send-btn svg {
  transform: rotate(-45deg);
}

.send-btn svg path {
  stroke-width: 2.4;
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

.mobile-chat-topbar,
.mobile-menu-panel,
.mobile-call-screen {
  display: none;
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

@media (max-width: 768px) {
  .app-shell.expanded {
    background: #f7fafd;
  }

  .layout-fullscreen {
    position: relative;
    height: 100dvh;
    min-height: 100dvh;
    --mobile-bg-image: none;
  }

  .layout-fullscreen > .sidebar,
  .layout-fullscreen > .task-panel,
  .panel-chat > .chat-header {
    display: none;
  }

  .panel-chat {
    position: relative;
    min-width: 0;
    width: 100%;
    height: 100dvh;
    flex: 1 1 auto;
    border: none;
    box-shadow: none;
    color: #2f3a48;
    background:
      linear-gradient(180deg, rgba(248, 251, 255, 0.86), rgba(241, 247, 253, 0.9)),
      var(--mobile-bg-image),
      #f7fafd;
    background-size: cover;
    background-position: center;
  }

  .panel-chat::before {
    display: none;
  }

  .mobile-chat-topbar {
    position: relative;
    z-index: 4;
    height: calc(88px + env(safe-area-inset-top));
    padding: calc(24px + env(safe-area-inset-top)) 18px 12px;
    display: grid;
    grid-template-columns: 44px 1fr auto;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(250, 252, 255, 0.72);
    backdrop-filter: blur(16px);
  }

  .mobile-chat-person {
    text-align: center;
    min-width: 0;
  }

  .mobile-chat-person h2 {
    margin: 0;
    color: #263241;
    font-size: 22px;
    line-height: 1.05;
    font-weight: 500;
  }

  .mobile-chat-person span {
    display: block;
    margin-top: 5px;
    color: #7b8592;
    font-size: 15px;
    line-height: 1;
    letter-spacing: 0.02em;
  }

  .mobile-chat-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .mobile-icon-btn {
    width: 38px;
    height: 38px;
    padding: 0;
    border: 0;
    border-radius: 50%;
    color: #263241;
    background: transparent;
    display: grid;
    place-items: center;
  }

  .mobile-icon-btn svg,
  .mobile-compose-tool svg,
  .mobile-call-back svg,
  .mobile-call-tool svg,
  .mobile-live-title svg {
    width: 26px;
    height: 26px;
  }

  .mobile-icon-btn svg path,
  .mobile-compose-tool svg path,
  .mobile-call-back svg path,
  .mobile-call-tool svg path,
  .mobile-live-title svg path {
    fill: none;
    stroke: currentColor;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .mobile-menu-panel {
    position: absolute;
    top: calc(76px + env(safe-area-inset-top));
    right: 14px;
    width: min(278px, calc(100vw - 28px));
    max-height: min(420px, calc(100dvh - 112px));
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    overflow-y: auto;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 18px 48px rgba(15, 23, 42, 0.16);
    backdrop-filter: blur(18px);
  }

  .mobile-menu-action,
  .mobile-history-item {
    width: 100%;
    border: 0;
    text-align: left;
    color: #243041;
    background: rgba(241, 245, 249, 0.72);
    border-radius: 12px;
    cursor: pointer;
  }

  .mobile-menu-action {
    padding: 12px 14px;
    font-size: 15px;
    font-weight: 650;
  }

  .mobile-menu-title {
    padding: 5px 4px 0;
    color: #7b8592;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .mobile-history-item {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
  }

  .mobile-history-item.active {
    color: #1d4ed8;
    background: rgba(219, 234, 254, 0.9);
  }

  .mobile-history-item span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
  }

  .mobile-history-item small {
    color: #8a94a3;
    font-size: 11px;
  }

  .messages-container {
    padding: 30px 18px 16px;
    gap: 26px;
    background: transparent;
  }

  .message {
    max-width: 88%;
    gap: 10px;
    align-items: flex-end;
  }

  .message.is-user {
    max-width: 72%;
  }

  .message-avatar {
    width: 38px;
    height: 38px;
  }

  .bot-avatar {
    overflow: hidden;
    background: #ffffff;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
  }

  .bot-avatar span {
    display: none;
  }

  .mobile-bot-avatar-image {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 50%;
  }

  .message-content {
    padding: 15px 17px;
    border-radius: 4px 18px 18px 18px;
    background: rgba(255, 255, 255, 0.78);
    box-shadow: 0 8px 26px rgba(44, 57, 78, 0.08);
    backdrop-filter: blur(8px);
  }

  .is-user .message-content {
    color: #304052;
    border-radius: 18px 18px 4px 18px;
    background: rgba(226, 234, 246, 0.9);
    box-shadow: 0 8px 24px rgba(89, 116, 154, 0.12);
  }

  .message-content p,
  .is-user .message-content p {
    color: inherit;
    font-size: 17px;
    line-height: 1.55;
  }

  .agent-name {
    display: none;
  }

  .message-time,
  .is-user .message-time {
    margin-top: 10px;
    color: #96a0ad;
    font-size: 12px;
  }

  .typing-indicator {
    color: #8b96a5;
    background: transparent;
    padding: 4px 0 4px 54px;
    letter-spacing: 0.18em;
  }

  .typing-indicator::before,
  .typing-indicator::after {
    content: "✦";
    color: #a8b1bd;
  }

  .typing-dots {
    display: none;
  }

  .chat-input-form {
    align-items: flex-end;
    gap: 8px;
    padding: 10px 14px calc(18px + env(safe-area-inset-bottom));
    border-top: 0;
    background: rgba(247, 250, 253, 0.82);
    backdrop-filter: blur(14px);
  }

  .composer-main {
    flex: 1 1 auto;
    min-width: 0;
  }

  .attachment-chip {
    max-width: calc(100vw - 132px);
  }

  .chat-input-form .input-wrapper {
    min-width: 0;
  }

  .chat-input-form textarea {
    min-height: 54px;
    max-height: 96px;
    padding: 15px 14px;
    border: 0;
    border-radius: 999px;
    color: #2d3948;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: 0 10px 30px rgba(45, 57, 78, 0.08);
    font-size: 16px;
    line-height: 1.35;
  }

  .chat-input-form textarea::placeholder {
    color: #8d98a6;
  }

  .mobile-compose-tool {
    width: 44px;
    height: 44px;
    padding: 0;
    border: 0;
    border-radius: 50%;
    color: #6b7785;
    background: transparent;
    display: grid;
    place-items: center;
    flex: 0 0 auto;
  }

  .emoji-picker {
    right: -52px;
    grid-template-columns: repeat(6, 1fr);
    width: 228px;
  }

  .send-btn {
    min-width: 54px;
    width: 54px;
    height: 54px;
    padding: 0;
    border-radius: 50%;
    color: #ffffff;
    background: #26384d;
    box-shadow: 0 12px 28px rgba(38, 56, 77, 0.2);
  }

  .send-btn svg {
    transform: rotate(-45deg);
  }

  .send-btn svg path {
    stroke-width: 2.4;
  }

  .mobile-call-screen {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100dvh;
    padding: calc(74px + env(safe-area-inset-top)) 24px calc(26px + env(safe-area-inset-bottom));
    color: #2f3a48;
    background:
      linear-gradient(180deg, rgba(249, 252, 255, 0.88), rgba(237, 244, 251, 0.9)),
      var(--mobile-bg-image),
      #f7fafd;
    background-size: cover;
    background-position: center;
  }

  .mobile-call-bg {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      radial-gradient(circle at 32% 20%, rgba(255, 255, 255, 0.84), transparent 24%),
      radial-gradient(circle at 75% 42%, rgba(219, 234, 254, 0.56), transparent 26%);
    filter: blur(1px);
  }

  .mobile-call-back {
    position: absolute;
    top: calc(74px + env(safe-area-inset-top));
    left: 24px;
    z-index: 2;
    width: 52px;
    height: 52px;
    border: 1px solid rgba(203, 213, 225, 0.45);
    border-radius: 50%;
    color: #526171;
    background: rgba(255, 255, 255, 0.34);
    display: grid;
    place-items: center;
    backdrop-filter: blur(12px);
  }

  .mobile-call-body {
    position: relative;
    z-index: 1;
    width: 100%;
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 0;
  }

  .mobile-call-hero {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 172px 1fr;
    align-items: center;
    gap: 8px;
  }

  .mobile-call-avatar {
    width: 172px;
    height: 172px;
    border-radius: 50%;
    object-fit: cover;
    background: #ffffff;
    box-shadow: 0 18px 38px rgba(30, 41, 59, 0.14);
  }

  .mobile-wave {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    overflow: hidden;
    color: rgba(116, 127, 142, 0.42);
  }

  .mobile-wave span {
    width: 4px;
    height: 18px;
    border-radius: 999px;
    background: currentColor;
    animation: mobileWave 1.35s ease-in-out infinite;
  }

  .mobile-wave span:nth-child(2n) { height: 30px; animation-delay: -0.2s; }
  .mobile-wave span:nth-child(3n) { height: 42px; animation-delay: -0.45s; }
  .mobile-wave span:nth-child(5n) { height: 24px; animation-delay: -0.72s; }

  .mobile-call-name {
    margin: 44px 0 0;
    color: #263241;
    font-size: 42px;
    line-height: 1;
    font-weight: 500;
  }

  .mobile-call-state {
    margin-top: 18px;
    color: #8d98a6;
    font-size: 18px;
    letter-spacing: 0.28em;
  }

  .mobile-call-time {
    margin-top: 20px;
    color: #526171;
    font-size: 18px;
    letter-spacing: 0.22em;
  }

  .mobile-live-title {
    margin-top: 54px;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #7b8795;
    font-size: 17px;
  }

  .mobile-live-title svg {
    width: 22px;
    height: 22px;
  }

  .mobile-live-text {
    width: 100%;
    min-height: 64px;
    max-height: 118px;
    margin: 20px 0 0;
    padding: 18px 20px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.72);
    border-radius: 26px;
    color: #2f3a48;
    background: rgba(255, 255, 255, 0.42);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.74);
    text-align: center;
    font-size: 24px;
    line-height: 1.35;
    backdrop-filter: blur(12px);
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .mobile-call-controls {
    position: relative;
    z-index: 1;
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin-bottom: 30px;
  }

  .mobile-call-tool {
    min-width: 0;
    border: 0;
    color: #667382;
    background: transparent;
    display: grid;
    justify-items: center;
    gap: 12px;
  }

  .mobile-call-tool svg {
    width: 76px;
    height: 76px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.7);
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.42);
    box-shadow: 0 14px 28px rgba(30, 41, 59, 0.08);
    backdrop-filter: blur(12px);
  }

  .mobile-call-tool.active svg {
    color: #1d4ed8;
    background: rgba(219, 234, 254, 0.72);
  }

  .mobile-call-tool span {
    color: #8d98a6;
    font-size: 16px;
  }

  .mobile-end-call {
    position: relative;
    z-index: 1;
    width: 96px;
    height: 96px;
    border: 0;
    border-radius: 50%;
    color: #ffffff;
    background: #cf8d94;
    box-shadow: 0 18px 34px rgba(166, 85, 96, 0.24);
    display: grid;
    place-items: center;
  }

  .mobile-end-call svg {
    width: 44px;
    height: 44px;
  }

  .mobile-end-call svg path {
    fill: currentColor;
  }

  @media (max-height: 760px) {
    .mobile-call-screen {
      padding: calc(54px + env(safe-area-inset-top)) 24px calc(16px + env(safe-area-inset-bottom));
    }

    .mobile-call-back {
      top: calc(54px + env(safe-area-inset-top));
      width: 48px;
      height: 48px;
    }

    .mobile-call-body {
      justify-content: flex-start;
    }

    .mobile-call-hero {
      grid-template-columns: 1fr 128px 1fr;
    }

    .mobile-call-avatar {
      width: 128px;
      height: 128px;
    }

    .mobile-wave span {
      width: 3px;
    }

    .mobile-call-name {
      margin-top: 22px;
      font-size: 36px;
    }

    .mobile-call-state {
      margin-top: 10px;
      font-size: 16px;
      letter-spacing: 0.24em;
    }

    .mobile-call-time {
      margin-top: 12px;
      font-size: 17px;
    }

    .mobile-live-title {
      margin-top: 24px;
      font-size: 15px;
    }

    .mobile-live-text {
      min-height: 48px;
      max-height: 58px;
      margin-top: 12px;
      padding: 11px 16px;
      border-radius: 22px;
      font-size: 18px;
      line-height: 1.25;
    }

    .mobile-call-controls {
      gap: 10px;
      margin-bottom: 18px;
    }

    .mobile-call-tool {
      gap: 8px;
    }

    .mobile-call-tool svg {
      width: 64px;
      height: 64px;
      padding: 17px;
    }

    .mobile-call-tool span {
      font-size: 14px;
    }

    .mobile-end-call {
      width: 80px;
      height: 80px;
    }

    .mobile-end-call svg {
      width: 38px;
      height: 38px;
    }
  }

  @keyframes mobileWave {
    0%, 100% { transform: scaleY(0.55); opacity: 0.45; }
    50% { transform: scaleY(1); opacity: 0.9; }
  }
}

@media (max-width: 420px) {
  .mobile-chat-topbar {
    grid-template-columns: 40px 1fr auto;
    padding-left: 12px;
    padding-right: 12px;
  }

  .mobile-chat-actions {
    gap: 5px;
  }

  .mobile-icon-btn {
    width: 34px;
    height: 34px;
  }

  .mobile-call-hero {
    grid-template-columns: 1fr 146px 1fr;
  }

  .mobile-call-avatar {
    width: 146px;
    height: 146px;
  }

  .mobile-call-name {
    margin-top: 34px;
    font-size: 38px;
  }

  .mobile-call-controls {
    gap: 10px;
  }

  .mobile-call-tool svg {
    width: 68px;
    height: 68px;
    padding: 18px;
  }
}
</style>
