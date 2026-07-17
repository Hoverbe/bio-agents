const baseURL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:7777";

export function getVoiceWsUrl(sessionId: string): string {
  const url = new URL(baseURL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const basePath = url.pathname.replace(/\/$/, "");
  url.pathname = `${basePath}/voice/ws/${encodeURIComponent(sessionId)}`;
  url.search = "";
  return url.toString();
}

export function isVoiceWsSecure(): boolean {
  const url = new URL(baseURL);
  return url.protocol === "https:" || url.hostname === "localhost" || url.hostname === "127.0.0.1";
}

export interface ResearchRequest {
  username: string;
  topic: string;
  search_api?: string;
  history?: Array<{ role: string; content: string }>;
  attachments?: ResearchAttachment[];
}

export interface ResearchAttachment {
  filename: string;
  content: string;
  content_type?: string | null;
  truncated?: boolean;
  saved_path?: string | null;
  saved_url?: string | null;
}

export interface ParsedAttachment extends ResearchAttachment {
  size?: number | null;
  chars: number;
}

export interface DownloadFile {
  name: string;
  path: string;
  size: number;
  url: string;
  is_image: boolean;
}

export interface ResearchStreamEvent {
  type: string;
  [key: string]: unknown;
}

export interface ConversationRecord {
  id: number;
  conversation_type: string;
  request_text: string;
  response_text?: string | null;
  history_json?: Array<{ role: string; content: string }> | null;
  metadata_json?: {
    download_session_id?: string;
    download_files?: DownloadFile[];
    [key: string]: unknown;
  } | null;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ConversationHistoryResponse {
  conversations: ConversationRecord[];
}

export interface StreamOptions {
  signal?: AbortSignal;
}

async function requestJSON<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseURL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(errorText || `请求失败，状态码：${response.status}`);
  }
  return response.json();
}

export function getAdminConfig(): Promise<any> {
  return requestJSON("/admin/config");
}

export function saveMCPConfig(payload: any): Promise<any> {
  return requestJSON("/admin/mcp", { method: "POST", body: JSON.stringify(payload) });
}

export function deleteMCPConfig(name: string): Promise<any> {
  return requestJSON(`/admin/mcp/${encodeURIComponent(name)}`, { method: "DELETE" });
}

export function saveToolConfig(payload: any): Promise<any> {
  return requestJSON("/admin/tools", { method: "POST", body: JSON.stringify(payload) });
}

export function deleteToolConfig(name: string): Promise<any> {
  return requestJSON(`/admin/tools/${encodeURIComponent(name)}`, { method: "DELETE" });
}

export function saveSkillConfig(payload: any): Promise<any> {
  return requestJSON("/admin/skills", { method: "POST", body: JSON.stringify(payload) });
}

export function deleteSkillConfig(name: string): Promise<any> {
  return requestJSON(`/admin/skills/${encodeURIComponent(name)}`, { method: "DELETE" });
}

export function saveModelConfig(payload: any): Promise<any> {
  return requestJSON("/admin/models", { method: "POST", body: JSON.stringify(payload) });
}

export function activateModelConfig(name: string): Promise<any> {
  return requestJSON("/admin/models/active", { method: "POST", body: JSON.stringify({ name }) });
}

export function deleteModelConfig(name: string): Promise<any> {
  return requestJSON(`/admin/models/${encodeURIComponent(name)}`, { method: "DELETE" });
}

export function saveRAGConfig(payload: any): Promise<any> {
  return requestJSON("/admin/rag", { method: "POST", body: JSON.stringify(payload) });
}

export function getRAGDocuments(namespace = "default"): Promise<any> {
  return requestJSON(`/admin/rag/documents?namespace=${encodeURIComponent(namespace)}`);
}

export function uploadRAGDocument(formData: FormData): Promise<any> {
  return fetch(`${baseURL}/admin/rag/upload`, {
    method: "POST",
    body: formData
  }).then(async (response) => {
    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      throw new Error(errorText || `请求失败，状态码：${response.status}`);
    }
    return response.json();
  });
}

export function parseAttachmentFile(file: File): Promise<ParsedAttachment> {
  const formData = new FormData();
  formData.append("file", file);

  return fetch(`${baseURL}/attachments/parse`, {
    method: "POST",
    body: formData
  }).then(async (response) => {
    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      throw new Error(errorText || `请求失败，状态码：${response.status}`);
    }
    return response.json();
  });
}

export function getFileUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  return `${baseURL}${url.startsWith("/") ? url : `/${url}`}`;
}

export function listDownloadFiles(sessionId?: string): Promise<{ files: DownloadFile[] }> {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  return requestJSON(`/downloads${query}`);
}

export function startRAGDocument(source: string, namespace = "default"): Promise<any> {
  const formData = new FormData();
  formData.append("source", source);
  formData.append("namespace", namespace);
  return fetch(`${baseURL}/admin/rag/documents/start`, {
    method: "POST",
    body: formData
  }).then(async (response) => {
    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      throw new Error(errorText || `请求失败，状态码：${response.status}`);
    }
    return response.json();
  });
}

export function stopRAGDocument(source: string, namespace = "default"): Promise<any> {
  const formData = new FormData();
  formData.append("source", source);
  formData.append("namespace", namespace);
  return fetch(`${baseURL}/admin/rag/documents/stop`, {
    method: "POST",
    body: formData
  }).then(async (response) => {
    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      throw new Error(errorText || `请求失败，状态码：${response.status}`);
    }
    return response.json();
  });
}

export function deleteRAGDocument(source: string, namespace = "default"): Promise<any> {
  return requestJSON(`/admin/rag/documents?source=${encodeURIComponent(source)}&namespace=${encodeURIComponent(namespace)}`, { method: "DELETE" });
}

export function getConversationHistory(username: string): Promise<ConversationHistoryResponse> {
  return requestJSON(`/conversations/${encodeURIComponent(username)}`);
}

export function deleteConversation(username: string, conversationId: number): Promise<{ deleted: boolean; id: number }> {
  return requestJSON(
    `/conversations/${encodeURIComponent(username)}/${encodeURIComponent(String(conversationId))}`,
    { method: "DELETE" }
  );
}

// 发送聊天消息
export async function sendMessage(username: string, message: string): Promise<string> {
  const response = await fetch(`${baseURL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      message,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(errorText || `请求失败，状态码：${response.status}`);
  }

  const data = await response.json();
  return data.response || data.message || "暂无响应";
}

export async function runResearchStream(
  payload: ResearchRequest,
  onEvent: (event: ResearchStreamEvent) => void,
  options: StreamOptions = {}
): Promise<void> {
  const response = await fetch(`${baseURL}/research/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream"
    },
    body: JSON.stringify(payload),
    signal: options.signal
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(
      errorText || `研究请求失败，状态码：${response.status}`
    );
  }

  const body = response.body;
  if (!body) {
    throw new Error("浏览器不支持流式响应，无法获取研究进度");
  }

  const reader = body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);

      if (rawEvent.startsWith("data:")) {
        const dataPayload = rawEvent.slice(5).trim();
        if (dataPayload) {
          try {
            const event = JSON.parse(dataPayload) as ResearchStreamEvent;
            onEvent(event);

            if (event.type === "error" || event.type === "done") {
              return;
            }
          } catch (error) {
            console.error("解析流式事件失败：", error, dataPayload);
          }
        }
      }

      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      if (buffer.trim()) {
        const rawEvent = buffer.trim();
        if (rawEvent.startsWith("data:")) {
          const dataPayload = rawEvent.slice(5).trim();
          if (dataPayload) {
            try {
              const event = JSON.parse(dataPayload) as ResearchStreamEvent;
              onEvent(event);
            } catch (error) {
              console.error("解析流式事件失败：", error, dataPayload);
            }
          }
        }
      }
      break;
    }
  }
}
