const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:7777";
export function getVoiceWsUrl(sessionId) {
    const url = new URL(baseURL);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = `/voice/ws/${encodeURIComponent(sessionId)}`;
    url.search = "";
    return url.toString();
}
export function isVoiceWsSecure() {
    const url = new URL(baseURL);
    return url.protocol === "https:" || url.hostname === "localhost" || url.hostname === "127.0.0.1";
}
async function requestJSON(path, options = {}) {
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
export function getAdminConfig() {
    return requestJSON("/admin/config");
}
export function saveMCPConfig(payload) {
    return requestJSON("/admin/mcp", { method: "POST", body: JSON.stringify(payload) });
}
export function deleteMCPConfig(name) {
    return requestJSON(`/admin/mcp/${encodeURIComponent(name)}`, { method: "DELETE" });
}
export function saveToolConfig(payload) {
    return requestJSON("/admin/tools", { method: "POST", body: JSON.stringify(payload) });
}
export function deleteToolConfig(name) {
    return requestJSON(`/admin/tools/${encodeURIComponent(name)}`, { method: "DELETE" });
}
export function saveSkillConfig(payload) {
    return requestJSON("/admin/skills", { method: "POST", body: JSON.stringify(payload) });
}
export function deleteSkillConfig(name) {
    return requestJSON(`/admin/skills/${encodeURIComponent(name)}`, { method: "DELETE" });
}
export function saveRAGConfig(payload) {
    return requestJSON("/admin/rag", { method: "POST", body: JSON.stringify(payload) });
}
export function getRAGDocuments(namespace = "default") {
    return requestJSON(`/admin/rag/documents?namespace=${encodeURIComponent(namespace)}`);
}
export function uploadRAGDocument(formData) {
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
export function startRAGDocument(source, namespace = "default") {
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
export function stopRAGDocument(source, namespace = "default") {
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
export function deleteRAGDocument(source, namespace = "default") {
    return requestJSON(`/admin/rag/documents?source=${encodeURIComponent(source)}&namespace=${encodeURIComponent(namespace)}`, { method: "DELETE" });
}
// 发送聊天消息
export async function sendMessage(username, message) {
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
export async function runResearchStream(payload, onEvent, options = {}) {
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
        throw new Error(errorText || `研究请求失败，状态码：${response.status}`);
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
                        const event = JSON.parse(dataPayload);
                        onEvent(event);
                        if (event.type === "error" || event.type === "done") {
                            return;
                        }
                    }
                    catch (error) {
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
                            const event = JSON.parse(dataPayload);
                            onEvent(event);
                        }
                        catch (error) {
                            console.error("解析流式事件失败：", error, dataPayload);
                        }
                    }
                }
            }
            break;
        }
    }
}
