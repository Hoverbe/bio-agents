<template>
  <section class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand-card">
        <div class="brand-logo">BA</div>
        <div>
          <h1>Bio-Agent Admin</h1>
          <p>全局后台管理系统</p>
        </div>
      </div>

      <nav class="admin-nav">
        <button
          v-for="item in navItems"
          :key="item.key"
          :class="['nav-item', { active: activeSection === item.key }]"
          @click="activeSection = item.key"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>
            <strong>{{ item.label }}</strong>
            <small>{{ item.desc }}</small>
          </span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <a href="/">返回用户端</a>
        <span>配置保存后立即影响所有用户</span>
      </div>
    </aside>

    <main class="admin-main">
      <header class="topbar">
        <div>
          <p class="eyebrow">Global Configuration</p>
          <h2>{{ currentNav?.label || "控制台" }}</h2>
          <p>{{ currentNav?.headline || "管理全局配置和运行状态。" }}</p>
        </div>
        <div class="topbar-actions">
          <span :class="['status-pill', loading ? 'syncing' : 'online']">
            {{ loading ? "同步中" : "服务在线" }}
          </span>
          <button class="primary" :disabled="loading" @click="loadConfig">
            {{ loading ? "刷新中..." : "刷新配置" }}
          </button>
        </div>
      </header>

      <p v-if="message" class="notice">{{ message }}</p>

      <section class="metric-grid">
        <article class="metric-card">
          <span>MCP 服务</span>
          <strong>{{ mcpConfigs.length }}</strong>
          <small>{{ runtimeMCP.length }} 个运行中</small>
        </article>
        <article class="metric-card">
          <span>Tool 工具</span>
          <strong>{{ toolConfigs.length }}</strong>
          <small>{{ runtimeTools.length }} 个运行中</small>
        </article>
        <article class="metric-card">
          <span>Skill 流程</span>
          <strong>{{ skills.length }}</strong>
          <small>{{ enabledCount(skills) }} 个已启用</small>
        </article>
        <article class="metric-card">
          <span>当前模型</span>
          <strong class="model-metric">{{ modelInfo.model_name || "未配置" }}</strong>
          <small>{{ modelInfo.provider || "auto" }} · {{ modelConfigs.length }} 个配置</small>
        </article>
        <article class="metric-card">
          <span>RAG 知识块</span>
          <strong>{{ ragStats.total_chunks || 0 }}</strong>
          <small>{{ ragForm.enabled ? "检索已启用" : "检索已禁用" }}</small>
        </article>
      </section>

      <section v-show="activeSection === 'overview'" class="content-grid">
        <article class="admin-card large-card">
          <header>
            <div>
              <h3>系统总览</h3>
              <p>查看当前全局配置数量、运行状态和 RAG 数据统计。</p>
            </div>
          </header>
          <div class="overview-grid">
            <div>
              <h4>运行中的 MCP</h4>
              <ConfigList :items="runtimeMCP" readonly />
            </div>
            <div>
              <h4>运行中的 Tool</h4>
              <ConfigList :items="runtimeTools" readonly />
            </div>
          </div>
        </article>

        <article class="admin-card">
          <header>
            <div>
              <h3>RAG 统计</h3>
              <p>知识库命名空间与数据量。</p>
            </div>
          </header>
          <div class="stats"><pre>{{ JSON.stringify(ragStats, null, 2) }}</pre></div>
        </article>
      </section>

      <section v-show="activeSection === 'mcp'" class="content-grid two-column">
        <article class="admin-card editor-card">
          <header>
            <div>
              <h3>MCP 服务配置</h3>
              <p>添加或编辑全局 MCP 服务。</p>
            </div>
          </header>
          <div class="form-grid">
            <label><span>服务名称</span><input v-model="mcpForm.name" placeholder="如 bioinformatics" /></label>
            <label><span>服务描述</span><input v-model="mcpForm.description" placeholder="服务描述" /></label>
            <label><span>启动命令</span><textarea v-model="mcpCommandText" placeholder="server_command，每行一个参数，如：uvx" /></label>
            <label><span>启动参数</span><textarea v-model="mcpArgsText" placeholder="server_args，每行一个参数" /></label>
            <label><span>环境变量</span><textarea v-model="mcpEnvText" placeholder="每行 KEY=VALUE" /></label>
            <label class="check"><input v-model="mcpForm.enabled" type="checkbox" /> 启用该 MCP</label>
            <button class="primary" @click="saveMCP">保存 MCP</button>
          </div>
        </article>
        <article class="admin-card list-card">
          <header><div><h3>MCP 列表</h3><p>{{ mcpConfigs.length }} 个全局配置</p></div></header>
          <ConfigList :items="mcpConfigs" @edit="editMCP" @remove="removeMCP" />
        </article>
      </section>

      <section v-show="activeSection === 'tools'" class="content-grid two-column">
        <article class="admin-card editor-card">
          <header><div><h3>Tool 工具配置</h3><p>管理内置或自定义工具的启用状态和参数。</p></div></header>
          <div class="form-grid">
            <label><span>工具名称</span><input v-model="toolForm.name" placeholder="如 terminal" /></label>
            <label><span>工具描述</span><input v-model="toolForm.description" placeholder="工具描述" /></label>
            <label><span>工具类型</span><input v-model="toolForm.type" placeholder="builtin/custom" /></label>
            <label><span>JSON 配置</span><textarea v-model="toolConfigText" placeholder='如 {"timeout":30}' /></label>
            <label class="check"><input v-model="toolForm.enabled" type="checkbox" /> 启用该 Tool</label>
            <button class="primary" @click="saveTool">保存 Tool</button>
          </div>
        </article>
        <article class="admin-card list-card">
          <header><div><h3>Tool 列表</h3><p>{{ toolConfigs.length }} 个全局配置</p></div></header>
          <ConfigList :items="toolConfigs" @edit="editTool" @remove="removeTool" />
        </article>
      </section>

      <section v-show="activeSection === 'skills'" class="content-grid two-column wide-editor">
        <article class="admin-card editor-card">
          <header><div><h3>Skill 流程配置</h3><p>维护可复用的业务流程和提示模板。</p></div></header>
          <div class="form-grid">
            <label><span>Skill 名称</span><input v-model="skillForm.name" placeholder="如 primer_design" /></label>
            <label><span>Skill 描述</span><input v-model="skillForm.description" placeholder="Skill 描述" /></label>
            <label><span>Skill 正文</span><textarea v-model="skillForm.body" class="large" placeholder="Skill 正文内容" /></label>
            <label class="check"><input v-model="skillForm.enabled" type="checkbox" /> 启用该 Skill</label>
            <button class="primary" @click="saveSkill">保存 Skill</button>
          </div>
        </article>
        <article class="admin-card list-card">
          <header><div><h3>Skill 列表</h3><p>{{ skills.length }} 个全局配置</p></div></header>
          <ConfigList :items="skills" @edit="editSkill" @remove="removeSkill" />
        </article>
      </section>

      <section v-show="activeSection === 'models'" class="content-grid two-column">
        <article class="admin-card editor-card">
          <header><div><h3>模型管理</h3><p>配置 OpenAI 兼容模型服务，保存后会立即切换当前模型。</p></div></header>
          <div class="model-current">
            <div>
              <span>当前模型</span>
              <strong>{{ modelInfo.model_name || "未配置" }}</strong>
              <p>{{ modelInfo.base_url || "暂无服务地址" }}</p>
            </div>
            <div>
              <span>Provider</span>
              <strong>{{ modelInfo.provider || "auto" }}</strong>
              <p>API Key：{{ modelInfo.has_api_key ? modelInfo.api_key_mask : "未配置" }}</p>
            </div>
          </div>
          <div class="form-grid">
            <label><span>Model Name</span><input v-model="modelForm.model_name" placeholder="如 gpt-4o-mini" autocomplete="off" /></label>
            <label><span>URL</span><input v-model="modelForm.base_url" placeholder="如 https://api.openai.com/v1" autocomplete="off" /></label>
            <label>
              <span>API Key</span>
              <input
                v-model="modelForm.api_key"
                type="password"
                placeholder="留空则沿用已保存的 key"
                autocomplete="new-password"
              />
            </label>
            <small class="hint">页面不会回显完整 API Key；保存后只显示脱敏状态。</small>
            <label class="check"><input v-model="modelForm.enabled" type="checkbox" /> 启用该模型配置</label>
            <button class="primary" @click="saveModel">
              {{ modelForm.enabled ? "保存并切换模型" : "保存模型配置" }}
            </button>
          </div>
        </article>
        <article class="admin-card list-card">
          <header><div><h3>模型列表</h3><p>{{ modelConfigs.length }} 个全局模型配置，可快速切换</p></div></header>
          <div class="model-list">
            <div v-for="item in modelConfigs" :key="item.name" class="config-item">
              <div class="config-meta">
                <strong>{{ item.model_name || item.name }}</strong>
                <p>{{ item.enabled === false ? "未启用" : "启用" }} · {{ item.base_url }} · Key {{ item.has_api_key ? item.api_key_mask : "未配置" }}</p>
              </div>
              <div class="row-actions">
                <button :disabled="modelInfo.name === item.name" @click="activateModel(item.name)">
                  {{ modelInfo.name === item.name ? "当前" : "切换" }}
                </button>
                <button @click="editModel(item)">编辑</button>
                <button class="danger" @click="removeModel(item.name)">删除</button>
              </div>
            </div>
            <div v-if="modelConfigs.length === 0" class="empty-list">暂无模型配置</div>
          </div>
        </article>
      </section>

      <section v-show="activeSection === 'rag'" class="content-grid two-column">
        <article class="admin-card editor-card">
          <header><div><h3>RAG 检索配置</h3><p>设置全局默认知识库检索参数，并上传 PDF、TXT、Word、Excel、Markdown 等文本文件。</p></div></header>
          <div class="form-grid">
            <label><span>默认 namespace</span><input v-model="ragForm.namespace" placeholder="default" /></label>
            <label><span>默认 top_k</span><input v-model.number="ragForm.top_k" type="number" min="1" max="50" /></label>
            <label><span>chunk_size</span><input v-model.number="ragForm.chunk_size" type="number" min="100" max="10000" /></label>
            <label><span>chunk_overlap</span><input v-model.number="ragForm.chunk_overlap" type="number" min="0" max="5000" /></label>
            <label class="check"><input v-model="ragForm.enabled" type="checkbox" /> 启用 RAG 检索</label>
            <button class="primary" @click="saveRAG">保存 RAG</button>
            <label><span>上传 RAG 文本</span><input type="file" accept=".pdf,.txt,.md,.markdown,.doc,.docx,.xls,.xlsx,.csv" @change="handleRAGFileChange" /></label>
            <button class="primary" :disabled="loading || !ragFile" @click="uploadRAGFile">
              {{ ragFile ? `上传：${ragFile.name}` : "选择文件后上传" }}
            </button>
            <small class="hint">支持 PDF、TXT、Word、Excel、CSV、Markdown，上传后自动切分并加入当前 namespace。</small>
          </div>
        </article>
        <article class="admin-card list-card">
          <header><div><h3>RAG 文档</h3><p>{{ ragDocuments.length }} 个文档，可启动、停止或删除</p></div></header>
          <div class="rag-doc-list">
            <div v-for="doc in ragDocuments" :key="doc.source" class="rag-doc-item">
              <div class="config-meta">
                <strong>{{ doc.name }}</strong>
                <p>{{ doc.status === 'active' ? '运行中' : '已停止' }} · {{ doc.chunk_count }} 个知识块</p>
              </div>
              <div class="row-actions">
                <button v-if="doc.status !== 'active'" @click="startRAGDoc(doc.source)">启动</button>
                <button v-else @click="stopRAGDoc(doc.source)">停止</button>
                <button class="danger" @click="removeRAGDoc(doc.source)">删除</button>
              </div>
            </div>
            <div v-if="ragDocuments.length === 0" class="empty-list">暂无 RAG 文档</div>
          </div>
          <div class="stats compact"><pre>{{ JSON.stringify(ragStats, null, 2) }}</pre></div>
        </article>
      </section>
    </main>
  </section>
</template>

<script lang="ts" setup>
import { computed, defineComponent, h, onMounted, ref } from "vue";
import {
  activateModelConfig,
  deleteModelConfig,
  deleteMCPConfig,
  deleteRAGDocument,
  deleteSkillConfig,
  deleteToolConfig,
  getAdminConfig,
  getRAGDocuments,
  saveMCPConfig,
  saveModelConfig,
  saveRAGConfig,
  saveSkillConfig,
  saveToolConfig,
  startRAGDocument,
  stopRAGDocument,
  uploadRAGDocument
} from "../services/api";

const ConfigList = defineComponent({
  props: {
    items: { type: Array, default: () => [] },
    readonly: { type: Boolean, default: false }
  },
  emits: ["edit", "remove"],
  setup(props, { emit }) {
    return () => h("div", { class: "config-list" }, (props.items as any[]).length
      ? (props.items as any[]).map((item) =>
        h("div", { class: "config-item", key: String(item.name || item.description) }, [
          h("div", { class: "config-meta" }, [
            h("strong", String(item.name || "未命名")),
            h("p", `${item.enabled === false ? "未启用" : "启用"} · ${item.description || item.type || "暂无描述"}`)
          ]),
          props.readonly ? null : h("div", { class: "row-actions" }, [
            h("button", { onClick: () => emit("edit", item) }, "编辑"),
            h("button", { class: "danger", onClick: () => emit("remove", item.name) }, "删除")
          ])
        ])
      )
      : [h("div", { class: "empty-list" }, "暂无数据")]
    );
  }
});

const navItems = [
  { key: "overview", label: "控制台", icon: "总", desc: "运行概览", headline: "查看全局配置和运行状态。" },
  { key: "mcp", label: "MCP 管理", icon: "M", desc: "服务连接", headline: "管理所有用户共享的 MCP 服务。" },
  { key: "tools", label: "Tool 管理", icon: "T", desc: "工具能力", headline: "配置系统可调用的全局工具。" },
  { key: "skills", label: "Skill 管理", icon: "S", desc: "流程模板", headline: "维护可复用的全局 Skill 流程。" },
  { key: "models", label: "模型管理", icon: "AI", desc: "模型切换", headline: "查看当前模型并快速切换 OpenAI 兼容服务。" },
  { key: "rag", label: "RAG 管理", icon: "R", desc: "知识库", headline: "配置全局 RAG 检索行为。" }
];

const activeSection = ref("overview");
const currentNav = computed(() => navItems.find((item) => item.key === activeSection.value));
const loading = ref(false);
const message = ref("");
const runtimeMCP = ref<any[]>([]);
const runtimeTools = ref<any[]>([]);
const mcpConfigs = ref<any[]>([]);
const toolConfigs = ref<any[]>([]);
const skills = ref<any[]>([]);
const modelInfo = ref<Record<string, any>>({});
const modelConfigs = ref<any[]>([]);
const ragStats = ref<Record<string, any>>({});
const ragDocuments = ref<any[]>([]);
const ragFile = ref<File | null>(null);

const mcpForm = ref({ name: "", description: "", enabled: true });
const mcpCommandText = ref("");
const mcpArgsText = ref("");
const mcpEnvText = ref("");
const toolForm = ref({ name: "", description: "", type: "builtin", enabled: true });
const toolConfigText = ref("{}");
const skillForm = ref({ name: "", description: "", body: "", enabled: true });
const modelForm = ref({ model_name: "", base_url: "", api_key: "", enabled: true });
const ragForm = ref({ namespace: "default", top_k: 5, chunk_size: 900, chunk_overlap: 120, enabled: true });

function enabledCount(items: any[]) {
  return items.filter((item) => item.enabled !== false).length;
}

function show(text: string) {
  message.value = text;
  window.setTimeout(() => (message.value = ""), 2500);
}

async function loadConfig() {
  loading.value = true;
  try {
    const data = await getAdminConfig();
    runtimeMCP.value = data.mcp || [];
    runtimeTools.value = data.tools || [];
    mcpConfigs.value = data.mcp_config || [];
    toolConfigs.value = data.tool_config || [];
    skills.value = data.skills || [];
    modelInfo.value = data.model || {};
    modelConfigs.value = data.model_config || [];
    ragStats.value = data.rag || {};
    ragForm.value = { namespace: "default", top_k: 5, chunk_size: 900, chunk_overlap: 120, enabled: true, ...(data.rag_config || {}) };
    await loadRAGDocuments();
  } catch (error) {
    show(error instanceof Error ? error.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

async function saveMCP() {
  await saveMCPConfig({ ...mcpForm.value, server_command: mcpCommandText.value, server_args: mcpArgsText.value, env: mcpEnvText.value });
  show("MCP 配置已保存");
  await loadConfig();
}

function editMCP(item: any) {
  activeSection.value = "mcp";
  mcpForm.value = { name: item.name || "", description: item.description || "", enabled: item.enabled !== false };
  mcpCommandText.value = (item.server_command || []).join("\n");
  mcpArgsText.value = (item.server_args || []).join("\n");
  mcpEnvText.value = Object.entries(item.env || {}).map(([key, val]) => `${key}=${val}`).join("\n");
}

async function removeMCP(name: string) {
  if (!name) return;
  await deleteMCPConfig(name);
  show("MCP 配置已删除");
  await loadConfig();
}

async function saveTool() {
  let config = {};
  try {
    config = JSON.parse(toolConfigText.value || "{}");
  } catch {
    show("Tool 配置 JSON 格式错误");
    return;
  }
  await saveToolConfig({ ...toolForm.value, config });
  show("Tool 配置已保存");
  await loadConfig();
}

function editTool(item: any) {
  activeSection.value = "tools";
  toolForm.value = { name: item.name || "", description: item.description || "", type: item.type || "builtin", enabled: item.enabled !== false };
  toolConfigText.value = JSON.stringify(item.config || {}, null, 2);
}

async function removeTool(name: string) {
  if (!name) return;
  await deleteToolConfig(name);
  show("Tool 配置已删除");
  await loadConfig();
}

async function saveSkill() {
  await saveSkillConfig(skillForm.value);
  show("Skill 已保存");
  await loadConfig();
}

function editSkill(item: any) {
  activeSection.value = "skills";
  skillForm.value = { name: item.name || "", description: item.description || "", body: item.body || "", enabled: item.enabled !== false };
}

async function removeSkill(name: string) {
  if (!name) return;
  await deleteSkillConfig(name);
  show("Skill 已删除");
  await loadConfig();
}

async function saveModel() {
  if (!modelForm.value.model_name.trim() || !modelForm.value.base_url.trim()) {
    show("请填写 Model Name 和 URL");
    return;
  }
  try {
    await saveModelConfig({
      ...modelForm.value,
      model_name: modelForm.value.model_name.trim(),
      base_url: modelForm.value.base_url.trim()
    });
    modelForm.value.api_key = "";
    show(modelForm.value.enabled ? "模型配置已保存并切换" : "模型配置已保存");
    await loadConfig();
  } catch (error) {
    show(error instanceof Error ? error.message : "模型配置保存失败");
  }
}

function editModel(item: any) {
  activeSection.value = "models";
  modelForm.value = {
    model_name: item.model_name || item.name || "",
    base_url: item.base_url || "",
    api_key: "",
    enabled: item.enabled !== false
  };
}

async function activateModel(name: string) {
  if (!name) return;
  try {
    await activateModelConfig(name);
    show("模型已切换");
    await loadConfig();
  } catch (error) {
    show(error instanceof Error ? error.message : "模型切换失败");
  }
}

async function removeModel(name: string) {
  if (!name) return;
  try {
    await deleteModelConfig(name);
    show("模型配置已删除");
    await loadConfig();
  } catch (error) {
    show(error instanceof Error ? error.message : "模型配置删除失败");
  }
}

async function saveRAG() {
  await saveRAGConfig(ragForm.value);
  show("RAG 配置已保存");
  await loadConfig();
}

async function loadRAGDocuments() {
  const data = await getRAGDocuments(ragForm.value.namespace || "default");
  ragDocuments.value = data.documents || [];
}

function handleRAGFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  ragFile.value = input.files?.[0] || null;
}

async function uploadRAGFile() {
  if (!ragFile.value) return;
  const formData = new FormData();
  formData.append("file", ragFile.value);
  formData.append("namespace", ragForm.value.namespace || "default");
  await uploadRAGDocument(formData);
  show("RAG 文档已上传");
  ragFile.value = null;
  await loadConfig();
}

async function startRAGDoc(source: string) {
  await startRAGDocument(source, ragForm.value.namespace || "default");
  show("RAG 文档已启动");
  await loadConfig();
}

async function stopRAGDoc(source: string) {
  await stopRAGDocument(source, ragForm.value.namespace || "default");
  show("RAG 文档已停止");
  await loadConfig();
}

async function removeRAGDoc(source: string) {
  await deleteRAGDocument(source, ragForm.value.namespace || "default");
  show("RAG 文档已删除");
  await loadConfig();
}

onMounted(loadConfig);
</script>

<style scoped>
.admin-shell { min-height: 100vh; display: flex; background: #eef2f7; color: #0f172a; }
.admin-sidebar { width: 288px; padding: 22px; display: flex; flex-direction: column; gap: 20px; background: linear-gradient(180deg, #0f172a, #1e1b4b); color: #e5e7eb; box-sizing: border-box; }
.brand-card { display: flex; gap: 12px; align-items: center; padding: 14px; border-radius: 20px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.12); }
.brand-logo { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 14px; background: linear-gradient(135deg, #60a5fa, #a78bfa); color: white; font-weight: 800; }
.brand-card h1 { margin: 0; font-size: 16px; }
.brand-card p { margin: 4px 0 0; color: #cbd5e1; font-size: 12px; }
.admin-nav { display: grid; gap: 8px; }
.nav-item { width: 100%; display: flex; gap: 12px; align-items: center; padding: 12px; border: 1px solid transparent; border-radius: 16px; background: transparent; color: #cbd5e1; cursor: pointer; text-align: left; }
.nav-item:hover, .nav-item.active { background: rgba(255,255,255,.1); border-color: rgba(255,255,255,.16); color: white; }
.nav-icon { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 12px; background: rgba(255,255,255,.12); font-weight: 800; }
.nav-item strong { display: block; font-size: 14px; }
.nav-item small { color: #94a3b8; }
.sidebar-footer { margin-top: auto; display: grid; gap: 10px; padding: 14px; border-radius: 18px; background: rgba(15,23,42,.45); }
.sidebar-footer a { color: white; text-decoration: none; font-weight: 700; }
.sidebar-footer span { color: #cbd5e1; font-size: 12px; line-height: 1.5; }
.admin-main { flex: 1; height: 100vh; overflow: auto; padding: 26px; box-sizing: border-box; }
.topbar { display: flex; justify-content: space-between; gap: 18px; align-items: center; margin-bottom: 18px; }
.eyebrow { margin: 0 0 4px; color: #2563eb; font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.topbar h2 { margin: 0 0 6px; font-size: 28px; }
.topbar p { margin: 0; color: #64748b; }
.topbar-actions { display: flex; gap: 12px; align-items: center; }
.status-pill { padding: 8px 12px; border-radius: 999px; font-size: 13px; font-weight: 700; }
.status-pill.online { background: #dcfce7; color: #166534; }
.status-pill.syncing { background: #fef3c7; color: #92400e; }
.notice { margin: 0 0 16px; padding: 12px 14px; border-radius: 14px; background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.metric-grid { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 14px; margin-bottom: 18px; }
.metric-card { padding: 18px; border-radius: 20px; background: white; border: 1px solid #e2e8f0; box-shadow: 0 14px 32px rgba(15,23,42,.06); }
.metric-card span { color: #64748b; font-size: 13px; }
.metric-card strong { display: block; margin: 8px 0 4px; font-size: 30px; }
.metric-card .model-metric { font-size: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.metric-card small { color: #94a3b8; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(320px, .8fr); gap: 16px; }
.content-grid.two-column { grid-template-columns: minmax(360px, .95fr) minmax(360px, 1.05fr); }
.content-grid.wide-editor { grid-template-columns: minmax(420px, 1.2fr) minmax(320px, .8fr); }
.admin-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 22px; padding: 20px; box-shadow: 0 16px 36px rgba(15,23,42,.07); }
.admin-card header { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 16px; }
.admin-card h3 { margin: 0 0 5px; color: #1e293b; }
.admin-card p { margin: 0; color: #64748b; font-size: 13px; line-height: 1.5; }
.overview-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.overview-grid h4 { margin: 0 0 10px; color: #334155; }
.form-grid { display: grid; gap: 12px; }
.form-grid label { display: grid; gap: 7px; color: #334155; font-size: 13px; font-weight: 700; }
.form-grid input, .form-grid textarea { width: 100%; box-sizing: border-box; padding: 11px 13px; border-radius: 13px; border: 1px solid #cbd5e1; background: #f8fafc; color: #0f172a; font: inherit; }
.form-grid input:focus, .form-grid textarea:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.12); background: white; }
.form-grid textarea { min-height: 86px; resize: vertical; }
.form-grid .large { min-height: 260px; }
.check { display: flex !important; grid-template-columns: auto 1fr !important; align-items: center; gap: 8px !important; font-weight: 700; }
.check input { width: auto; }
.primary { border: none; border-radius: 13px; padding: 11px 17px; background: linear-gradient(135deg, #2563eb, #7c3aed); color: #fff; font-weight: 800; cursor: pointer; }
.primary:hover { box-shadow: 0 10px 22px rgba(37,99,235,.22); }
.primary:disabled { opacity: .6; cursor: not-allowed; box-shadow: none; }
.config-list { display: grid; gap: 10px; }
.config-item { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 13px; border-radius: 16px; background: #f8fafc; border: 1px solid #e2e8f0; }
.config-meta { min-width: 0; }
.config-item strong { display: block; color: #0f172a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.config-item p { margin: 4px 0 0; color: #64748b; font-size: 13px; }
.empty-list { padding: 24px; border: 1px dashed #cbd5e1; border-radius: 16px; color: #94a3b8; text-align: center; background: #f8fafc; }
.row-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.row-actions button { border: 1px solid #cbd5e1; background: #fff; border-radius: 11px; padding: 8px 11px; cursor: pointer; font-weight: 700; color: #334155; }
.row-actions button:disabled { opacity: .55; cursor: not-allowed; }
.row-actions .danger { color: #dc2626; border-color: #fecaca; }
.model-current { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.model-current > div { min-width: 0; padding: 13px; border-radius: 16px; background: #f8fafc; border: 1px solid #e2e8f0; }
.model-current span { color: #64748b; font-size: 12px; font-weight: 800; text-transform: uppercase; }
.model-current strong { display: block; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #0f172a; }
.model-current p { margin-top: 6px; overflow-wrap: anywhere; }
.model-list { display: grid; gap: 10px; }
.stats pre { overflow: auto; max-height: 420px; min-height: 180px; padding: 14px; border-radius: 16px; background: #0f172a; color: #e2e8f0; line-height: 1.5; }
.stats.compact pre { max-height: 220px; min-height: 120px; margin-top: 14px; }
.hint { color: #64748b; line-height: 1.5; }
.rag-doc-list { display: grid; gap: 10px; }
.rag-doc-item { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 13px; border-radius: 16px; background: #f8fafc; border: 1px solid #e2e8f0; }
@media (max-width: 1180px) { .metric-grid { grid-template-columns: repeat(2, minmax(160px, 1fr)); } .content-grid, .content-grid.two-column, .content-grid.wide-editor { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .admin-shell { flex-direction: column; } .admin-sidebar { width: 100%; } .admin-main { height: auto; } .topbar, .topbar-actions { align-items: stretch; flex-direction: column; } .metric-grid, .overview-grid, .model-current { grid-template-columns: 1fr; } }
</style>
