/// <reference types="D:/Project/bio-agent/frontend/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="D:/Project/bio-agent/frontend/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { defineComponent, h, onMounted, ref } from "vue";
import { deleteMCPConfig, deleteSkillConfig, deleteToolConfig, getAdminConfig, saveMCPConfig, saveRAGConfig, saveSkillConfig, saveToolConfig } from "../services/api";
const ConfigList = defineComponent({
    props: { items: { type: Array, default: () => [] } },
    emits: ["edit", "remove"],
    setup(props, { emit }) {
        return () => h("div", { class: "config-list" }, props.items.map((item) => h("div", { class: "config-item", key: String(item.name || item.description) }, [
            h("div", [
                h("strong", String(item.name || "未命名")),
                h("p", `${item.enabled === false ? "未启用" : "启用"} · ${item.description || item.type || ""}`)
            ]),
            h("div", { class: "row-actions" }, [
                h("button", { onClick: () => emit("edit", item) }, "编辑"),
                h("button", { class: "danger", onClick: () => emit("remove", item.name) }, "删除")
            ])
        ])));
    }
});
const loading = ref(false);
const message = ref("");
const runtimeMCP = ref([]);
const runtimeTools = ref([]);
const mcpConfigs = ref([]);
const toolConfigs = ref([]);
const skills = ref([]);
const ragStats = ref({});
const mcpForm = ref({ name: "", description: "", enabled: true });
const mcpCommandText = ref("");
const mcpArgsText = ref("");
const mcpEnvText = ref("");
const toolForm = ref({ name: "", description: "", type: "builtin", enabled: true });
const toolConfigText = ref("{}");
const skillForm = ref({ name: "", description: "", body: "", enabled: true });
const ragForm = ref({ namespace: "default", top_k: 5, chunk_size: 900, chunk_overlap: 120, enabled: true });
function show(text) {
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
        ragStats.value = data.rag || {};
        ragForm.value = { namespace: "default", top_k: 5, chunk_size: 900, chunk_overlap: 120, enabled: true, ...(data.rag_config || {}) };
    }
    catch (error) {
        show(error instanceof Error ? error.message : "加载失败");
    }
    finally {
        loading.value = false;
    }
}
async function saveMCP() {
    await saveMCPConfig({ ...mcpForm.value, server_command: mcpCommandText.value, server_args: mcpArgsText.value, env: mcpEnvText.value });
    show("MCP 配置已保存");
    await loadConfig();
}
function editMCP(item) {
    mcpForm.value = { name: item.name || "", description: item.description || "", enabled: item.enabled !== false };
    mcpCommandText.value = (item.server_command || []).join("\n");
    mcpArgsText.value = (item.server_args || []).join("\n");
    mcpEnvText.value = Object.entries(item.env || {}).map(([key, val]) => `${key}=${val}`).join("\n");
}
async function removeMCP(name) {
    if (!name)
        return;
    await deleteMCPConfig(name);
    show("MCP 配置已删除");
    await loadConfig();
}
async function saveTool() {
    let config = {};
    try {
        config = JSON.parse(toolConfigText.value || "{}");
    }
    catch {
        show("Tool 配置 JSON 格式错误");
        return;
    }
    await saveToolConfig({ ...toolForm.value, config });
    show("Tool 配置已保存");
    await loadConfig();
}
function editTool(item) {
    toolForm.value = { name: item.name || "", description: item.description || "", type: item.type || "builtin", enabled: item.enabled !== false };
    toolConfigText.value = JSON.stringify(item.config || {}, null, 2);
}
async function removeTool(name) {
    if (!name)
        return;
    await deleteToolConfig(name);
    show("Tool 配置已删除");
    await loadConfig();
}
async function saveSkill() {
    await saveSkillConfig(skillForm.value);
    show("Skill 已保存");
    await loadConfig();
}
function editSkill(item) {
    skillForm.value = { name: item.name || "", description: item.description || "", body: item.body || "", enabled: item.enabled !== false };
}
async function removeSkill(name) {
    if (!name)
        return;
    await deleteSkillConfig(name);
    show("Skill 已删除");
    await loadConfig();
}
async function saveRAG() {
    await saveRAGConfig(ragForm.value);
    show("RAG 配置已保存");
    await loadConfig();
}
onMounted(loadConfig);
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['admin-header']} */ ;
/** @type {__VLS_StyleScopedClasses['admin-header']} */ ;
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['check']} */ ;
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
/** @type {__VLS_StyleScopedClasses['config-item']} */ ;
/** @type {__VLS_StyleScopedClasses['config-item']} */ ;
/** @type {__VLS_StyleScopedClasses['row-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['row-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['admin-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
/** @type {__VLS_StyleScopedClasses['wide']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "admin-page" },
});
/** @type {__VLS_StyleScopedClasses['admin-page']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "admin-header" },
});
/** @type {__VLS_StyleScopedClasses['admin-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.loadConfig) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
(__VLS_ctx.loading ? "刷新中..." : "刷新配置");
if (__VLS_ctx.message) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "notice" },
    });
    /** @type {__VLS_StyleScopedClasses['notice']} */ ;
    (__VLS_ctx.message);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "admin-grid" },
});
/** @type {__VLS_StyleScopedClasses['admin-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.article, __VLS_intrinsics.article)({
    ...{ class: "admin-card" },
});
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.mcpConfigs.length);
(__VLS_ctx.runtimeMCP.length);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-grid" },
});
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "服务名称，如 bioinformatics",
});
(__VLS_ctx.mcpForm.name);
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "服务描述",
});
(__VLS_ctx.mcpForm.description);
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.mcpCommandText),
    placeholder: "server_command，每行一个参数，如：uvx",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.mcpArgsText),
    placeholder: "server_args，每行一个参数",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.mcpEnvText),
    placeholder: "环境变量，每行 KEY=VALUE",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "check" },
});
/** @type {__VLS_StyleScopedClasses['check']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.mcpForm.enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveMCP) },
    ...{ class: "primary" },
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.ConfigList} */
ConfigList;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ 'onEdit': {} },
    ...{ 'onRemove': {} },
    items: (__VLS_ctx.mcpConfigs),
}));
const __VLS_2 = __VLS_1({
    ...{ 'onEdit': {} },
    ...{ 'onRemove': {} },
    items: (__VLS_ctx.mcpConfigs),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_5;
const __VLS_6 = ({ edit: {} },
    { onEdit: (__VLS_ctx.editMCP) });
const __VLS_7 = ({ remove: {} },
    { onRemove: (__VLS_ctx.removeMCP) });
var __VLS_3;
var __VLS_4;
__VLS_asFunctionalElement1(__VLS_intrinsics.article, __VLS_intrinsics.article)({
    ...{ class: "admin-card" },
});
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.toolConfigs.length);
(__VLS_ctx.runtimeTools.length);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-grid" },
});
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "工具名称，如 terminal",
});
(__VLS_ctx.toolForm.name);
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "工具描述",
});
(__VLS_ctx.toolForm.description);
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "工具类型，如 builtin/custom",
});
(__VLS_ctx.toolForm.type);
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.toolConfigText),
    placeholder: 'JSON 配置，如 {"timeout":30}',
});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "check" },
});
/** @type {__VLS_StyleScopedClasses['check']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.toolForm.enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveTool) },
    ...{ class: "primary" },
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
let __VLS_8;
/** @ts-ignore @type { | typeof __VLS_components.ConfigList} */
ConfigList;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
    ...{ 'onEdit': {} },
    ...{ 'onRemove': {} },
    items: (__VLS_ctx.toolConfigs),
}));
const __VLS_10 = __VLS_9({
    ...{ 'onEdit': {} },
    ...{ 'onRemove': {} },
    items: (__VLS_ctx.toolConfigs),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
let __VLS_13;
const __VLS_14 = ({ edit: {} },
    { onEdit: (__VLS_ctx.editTool) });
const __VLS_15 = ({ remove: {} },
    { onRemove: (__VLS_ctx.removeTool) });
var __VLS_11;
var __VLS_12;
__VLS_asFunctionalElement1(__VLS_intrinsics.article, __VLS_intrinsics.article)({
    ...{ class: "admin-card wide" },
});
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
/** @type {__VLS_StyleScopedClasses['wide']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.skills.length);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-grid skill-form" },
});
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['skill-form']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "Skill 名称，如 primer_design",
});
(__VLS_ctx.skillForm.name);
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "Skill 描述",
});
(__VLS_ctx.skillForm.description);
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.skillForm.body),
    ...{ class: "large" },
    placeholder: "Skill 正文内容",
});
/** @type {__VLS_StyleScopedClasses['large']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "check" },
});
/** @type {__VLS_StyleScopedClasses['check']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.skillForm.enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveSkill) },
    ...{ class: "primary" },
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
let __VLS_16;
/** @ts-ignore @type { | typeof __VLS_components.ConfigList} */
ConfigList;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent1(__VLS_16, new __VLS_16({
    ...{ 'onEdit': {} },
    ...{ 'onRemove': {} },
    items: (__VLS_ctx.skills),
}));
const __VLS_18 = __VLS_17({
    ...{ 'onEdit': {} },
    ...{ 'onRemove': {} },
    items: (__VLS_ctx.skills),
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
let __VLS_21;
const __VLS_22 = ({ edit: {} },
    { onEdit: (__VLS_ctx.editSkill) });
const __VLS_23 = ({ remove: {} },
    { onRemove: (__VLS_ctx.removeSkill) });
var __VLS_19;
var __VLS_20;
__VLS_asFunctionalElement1(__VLS_intrinsics.article, __VLS_intrinsics.article)({
    ...{ class: "admin-card" },
});
/** @type {__VLS_StyleScopedClasses['admin-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stats" },
});
/** @type {__VLS_StyleScopedClasses['stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({});
(JSON.stringify(__VLS_ctx.ragStats, null, 2));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-grid" },
});
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "默认 namespace",
});
(__VLS_ctx.ragForm.namespace);
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "50",
    placeholder: "默认 top_k",
});
(__VLS_ctx.ragForm.top_k);
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "100",
    max: "10000",
    placeholder: "chunk_size",
});
(__VLS_ctx.ragForm.chunk_size);
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0",
    max: "5000",
    placeholder: "chunk_overlap",
});
(__VLS_ctx.ragForm.chunk_overlap);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "check" },
});
/** @type {__VLS_StyleScopedClasses['check']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.ragForm.enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveRAG) },
    ...{ class: "primary" },
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
// @ts-ignore
[loadConfig, loading, loading, message, message, mcpConfigs, mcpConfigs, runtimeMCP, mcpForm, mcpForm, mcpForm, mcpCommandText, mcpArgsText, mcpEnvText, saveMCP, editMCP, removeMCP, toolConfigs, toolConfigs, runtimeTools, toolForm, toolForm, toolForm, toolForm, toolConfigText, saveTool, editTool, removeTool, skills, skills, skillForm, skillForm, skillForm, skillForm, saveSkill, editSkill, removeSkill, ragStats, ragForm, ragForm, ragForm, ragForm, ragForm, saveRAG,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
