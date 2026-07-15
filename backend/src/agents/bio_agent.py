from typing import List, Dict, Any, Iterator, Optional, Tuple
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from backend.src.agents.simple_agent import SimpleAgent
from backend.src.core.llm import HelloAgentsLLM
from backend.src.tools.builtin.protocol_tools import MCPTool
from backend.src.tools.terminalTool import TerminalTool, create_terminal_tool
from backend.src.tools.web_search_tool import WebSearchTool
from backend.src.config import settings
from backend.src.agents.prompt import MASTER_AGENT_PROMPT, KNOWLEDGE_AGENT_PROMPT, AUTOMATION_AGENT_PROMPT, QUERY_CLASSIFIER_PROMPT
from backend.src.rag_service import RAGService
from backend.src.admin_config import enabled_items, load_config

logger = logging.getLogger(__name__)


class BioAgent:
    """
    Bio-Agent主类 - 为生物科技公司设计的多智能体系统
    
    核心功能：
    1. 基础问答 - 通过knowledge_agent回答生物学问题和公司SOP查询
    2. MCP服务连接 - 连接内部数据库、外部API等服务
    3. 流程化Skill执行 - 执行预设的生物信息学分析流程
    4. Python脚本自动化 - 编写并执行定制化脚本
    5. 文件处理 - 解析上传的PDF/TXT等文档
    
    架构设计：
    - master_agent: 主控调度专家，负责任务分解和路由
    - knowledge_agent: 知识问答专家，处理纯文本问答
    - automation_agent: 自动化执行专家，处理需要操作的任务
    """

    def __init__(self):
        """初始化Bio-Agent多智能体系统"""
        try:
            logger.info("🔧 初始化Bio-Agent多智能体系统...")
            
            self.admin_config = load_config()

            # 初始化LLM客户端
            self.llm = HelloAgentsLLM()
            logger.info(f"✅ LLM客户端初始化完成，模型: {self.llm.model}")
            # self.mcp_tool = MCPTool(
            #     name="amap_mcp",
            #     server_command=["npx"],
            #     server_args=["-y", "@sugarforever/amap-mcp-server"],
            #     env={"AMAP_API_KEY": settings.amap_api_key},
            #     auto_expand=True
            # )
            # 初始化各个专业Agent
            self._init_agents()
            
            # 初始化MCP服务连接
            self._init_mcp_services()
            
            # 初始化文件处理器
            self._init_file_handlers()

            # 初始化 RAG 知识库
            rag_config = self.admin_config.get("rag", {})
            self.rag_service = RAGService(
                chunk_size=int(rag_config.get("chunk_size", 900)),
                chunk_overlap=int(rag_config.get("chunk_overlap", 120)),
            )
            
            # 任务执行历史
            self.task_history: List[Dict[str, Any]] = []
            
            logger.info("✅ Bio-Agent多智能体系统初始化完成")

        except Exception as e:
            logger.error(f"❌ 多智能体系统初始化失败: {str(e)}", exc_info=True)
            raise

    def _init_agents(self) -> None:
        """初始化各个专业Agent"""
        logger.info("  - 创建主控调度Agent...")
        self.master_agent = SimpleAgent(
            name="主控调度专家", 
            llm=self.llm, 
            system_prompt=MASTER_AGENT_PROMPT
        )

        logger.info("  - 创建自动化执行Agent...")
        # 创建终端工具（用于安全的命令行操作）
        try:
            # 工作目录使用项目根目录
            workspace = str(Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else Path.cwd())
            self.terminal_tool = create_terminal_tool(
                workspace=workspace,
                max_output_size=10 * 1024 * 1024,  # 10MB
                timeout=30  # 30秒
            )
            logger.info("  ✅ 终端工具初始化完成")
        except Exception as e:
            logger.error(f"  ❌ 终端工具初始化失败: {e}")
            self.terminal_tool = None

        self.automation_agent = SimpleAgent(
            name="自动化执行专家",
            llm=self.llm,
            system_prompt=AUTOMATION_AGENT_PROMPT,
            enable_tool_calling=True
        )

        # 注册终端工具到 automation_agent
        if self.terminal_tool and self._is_tool_enabled("terminal"):
            try:
                self.automation_agent.add_tool(self.terminal_tool)
                logger.info("  ✅ 终端工具已注册到自动化执行Agent")
            except Exception as e:
                logger.error(f"  ❌ 终端工具注册失败: {e}")

        if self._is_tool_enabled("web_search"):
            try:
                self.web_search_tool = WebSearchTool()
                self.automation_agent.add_tool(self.web_search_tool)
                logger.info("  ✅ Web Search工具已注册到自动化执行Agent")
            except Exception as e:
                logger.error(f"  ❌ Web Search工具注册失败: {e}")

        logger.info("  - 创建知识问答Agent...")
        self.knowledge_agent = SimpleAgent(
            name="知识问答专家", 
            llm=self.llm, 
            system_prompt=KNOWLEDGE_AGENT_PROMPT
        )

    def _init_mcp_services(self) -> None:
        """初始化MCP服务连接"""
        self.mcp_services: Dict[str, Any] = {}
        self.active_mcp_connections: Dict[str, MCPTool] = {}

        logger.info("  - 初始化MCP服务...")
        for item in enabled_items("mcp"):
            server_command = item.get("server_command") or []
            if isinstance(server_command, str):
                server_command = [line.strip() for line in server_command.splitlines() if line.strip()]
            server_args = item.get("server_args") or []
            if isinstance(server_args, str):
                server_args = [line.strip() for line in server_args.splitlines() if line.strip()]
            command = [*server_command, *server_args]
            if not item.get("name") or not command:
                continue
            self._register_mcp_service(
                item["name"],
                item.get("description", ""),
                server_command=command,
                env=item.get("env") or {},
            )

    def _init_file_handlers(self) -> None:
        #TODO 支持上传文件"txt", "pdf", "json", "csv", "fasta", "genbank"]
        """初始化文件处理器"""
        self.supported_file_types = ["txt", "pdf", "json", "csv", "fasta", "genbank"]
        logger.info(f"  - 支持的文件类型: {', '.join(self.supported_file_types)}")

    def _register_mcp_service(self, service_name: str, description: str, server_command: list, **kwargs) -> bool:
        """
        注册MCP服务并添加到自动化执行Agent
        
        Args:
            service_name: 服务名称
            description: 服务描述
            **kwargs: 服务配置参数
            
        Returns:
            bool: 是否注册成功
        """
        try:
            mcp_tool = MCPTool(
                name=service_name,
                description=description,
                server_command=server_command,
                **kwargs
            )
            self.mcp_services[service_name] = {
                'description': description,
                'tool': mcp_tool
            }
            
            # 将MCP工具添加到自动化执行Agent
            try:
                self.automation_agent.add_tool(mcp_tool)
                logger.info(f"✅ MCP服务 '{service_name}' 已注册并添加到自动化执行Agent")
            except Exception as e:
                logger.error(f"❌ MCP服务 '{service_name}' 添加到Agent失败: {str(e)}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"❌ MCP服务 '{service_name}' 注册失败: {str(e)}")
            return False

    def _is_tool_enabled(self, name: str) -> bool:
        for item in self.admin_config.get("tools", []):
            if item.get("name") == name:
                return bool(item.get("enabled", True))
        return True

    def reload_admin_config(self) -> None:
        self.admin_config = load_config()
        self._init_agents()
        self._init_mcp_services()
        rag_config = self.admin_config.get("rag", {})
        self.rag_service = RAGService(
            chunk_size=int(rag_config.get("chunk_size", 900)),
            chunk_overlap=int(rag_config.get("chunk_overlap", 120)),
        )

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """
        格式化对话历史为字符串，用于提示词

        Args:
            history: 对话历史列表，每个元素包含 'role' 和 'content'

        Returns:
            str: 格式化的对话历史字符串
        """
        if not history:
            return "无"
        
        history_lines = []
        for idx, item in enumerate(history[-10:]):  # 只保留最近10轮对话
            role = item.get('role', '')
            content = item.get('content', '')
            
            if role == 'user':
                history_lines.append(f"用户: {content}")
            elif role == 'assistant' or role == 'system':
                history_lines.append(f"助手: {content}")
            else:
                # 兼容其他角色格式
                agent_name = role.replace('_agent', '')
                history_lines.append(f"{agent_name}: {content}")
        
        return "\n".join(history_lines)

    def _normalize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """归一化主控Agent返回的任务字段"""
        for task in tasks:
            dependency = task.get('dependency')
            if isinstance(dependency, str):
                match = re.search(r'\d+', dependency)
                task['dependency'] = int(match.group()) if match else None
            elif dependency is not None and not isinstance(dependency, int):
                task['dependency'] = None
        return tasks

    def _parse_master_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析主控Agent的响应，提取子任务列表
        
        Args:
            response: 主控Agent的响应文本
            
        Returns:
            List[Dict]: 子任务列表
        """
        try:
            # 新格式：包含## 任务列表标记
            if "## 任务列表" in response:
                # 提取任务列表部分
                parts = response.split("## 任务列表")
                if len(parts) > 1:
                    task_content = parts[1].strip()
                    # 清理markdown代码块标记
                    if task_content.startswith('```'):
                        task_content = task_content[3:]
                        if task_content.lower().startswith('json'):
                            task_content = task_content[4:].strip()
                    if task_content.endswith('```'):
                        task_content = task_content[:-3].strip()
                        
                    tasks = json.loads(task_content)
                    if isinstance(tasks, list):
                        return self._normalize_tasks(tasks)
                    elif isinstance(tasks, dict) and 'tasks' in tasks:
                        return self._normalize_tasks(tasks['tasks'])
            
            # 旧格式：直接是JSON
            cleaned_response = response.strip()
            
            # 移除开头的 ```json 或 ``` 标记
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
                # 移除可能的 json 字样
                if cleaned_response.lower().startswith('json'):
                    cleaned_response = cleaned_response[4:].strip()
            
            # 移除结尾的 ``` 标记
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3].strip()
            
            # 清理可能的多余空白字符
            cleaned_response = cleaned_response.strip()
            
            try:
                tasks = json.loads(cleaned_response)
            except json.JSONDecodeError:
                match = re.search(r"\[[\s\S]*\]", cleaned_response)
                if not match:
                    match = re.search(r"\{[\s\S]*\}", cleaned_response)
                if not match:
                    raise
                tasks = json.loads(match.group(0))
            if isinstance(tasks, list):
                return self._normalize_tasks(tasks)
            elif isinstance(tasks, dict) and 'tasks' in tasks:
                return self._normalize_tasks(tasks['tasks'])
            else:
                return []
        except json.JSONDecodeError:
            logger.error(f"❌ 无法解析主控Agent响应: {response[:200]}...")
            return []

    def _build_web_search_task_description(self, query: str, conversation_history: str = "") -> str:
        """构造联网检索任务描述。"""
        parts = [
            "使用 web_search 工具搜索与用户问题直接相关的最新公开信息，并基于搜索结果直接给出简明准确的回答。",
            f"用户问题：{query.strip()}",
        ]
        history = conversation_history.strip()
        if history and history != "无":
            parts.append(f"对话历史：\n{history}")
        return "\n\n".join(parts)

    def _execute_task(self, task: Dict[str, Any], previous_results: str = "") -> Tuple[str, str]:
        """
        执行单个任务
        
        Args:
            task: 任务字典，包含step, agent, task_description, dependency
            previous_results: 前置步骤的执行结果
            
        Returns:
            Tuple[str, str]: (执行结果, 状态)
        """
        agent_name = task.get('agent', '')
        task_description = task.get('task_description', '')
        tool_agent_aliases = {"web_search_tool", "web_search", "terminal", "mcp"}
        if agent_name in tool_agent_aliases:
            task_description = f"使用 {agent_name} 工具执行：{task_description}"
            agent_name = "automation_agent"
        
        try:
            if agent_name == 'knowledge_agent':
                # 知识问答任务
                return self._execute_knowledge_task(task_description)
            elif agent_name == 'automation_agent':
                # 自动化执行任务
                return self._execute_automation_task(task_description, previous_results)
            else:
                logger.warning(f"⚠️ 未知的Agent类型: {agent_name}")
                return f"未知的Agent类型: {agent_name}", "failed"
        except Exception as e:
            logger.error(f"❌ 任务执行失败: {str(e)}", exc_info=True)
            return f"任务执行失败: {str(e)}", "failed"

    def _execute_web_qa_task(self, query: str, conversation_history: str = "") -> Tuple[str, str]:
        """执行需要联网搜索的问答任务。"""
        task_description = self._build_web_search_task_description(query, conversation_history)
        return self._execute_automation_task(task_description)

    def _execute_web_qa_task_stream(self, query: str, conversation_history: str = "") -> Iterator[str]:
        """流式执行需要联网搜索的问答任务。"""
        task_description = self._build_web_search_task_description(query, conversation_history)
        yield from self._execute_automation_task_stream(task_description)

    def _execute_knowledge_task(self, query: str, conversation_history: str = "") -> Tuple[str, str]:
        """
        执行知识问答任务

        Args:
            query: 用户问题
            conversation_history: 格式化的对话历史字符串

        Returns:
            Tuple[str, str]: (回答内容, 状态)
        """
        try:
            rag_config = self.admin_config.get("rag", {})
            context = ""
            if rag_config.get("enabled", True):
                context = self.rag_service.build_context(
                    query=query,
                    namespace=rag_config.get("namespace", "default"),
                    top_k=int(rag_config.get("top_k", 5)),
                )

            # 填充prompt模板
            formatted_prompt = KNOWLEDGE_AGENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                query=query,
                conversation_history=conversation_history or "无",
                context=context or "未检索到相关内部知识库内容"
            )

            # 更新Agent的系统提示词
            self.knowledge_agent.system_prompt = formatted_prompt

            # 执行问答
            response = self.knowledge_agent.run(input_text=query)
            # 清理响应：尝试解析JSON，如果失败则直接返回原文
            cleaned_response = self._clean_agent_response(response)
            return cleaned_response, "success"
        except Exception as e:
            logger.error(f"❌ 知识问答任务执行失败: {str(e)}")
            return f"问答失败: {str(e)}", "failed"

    def _clean_agent_response(self, response: str) -> str:
        """
        清理Agent响应，提取answer字段或移除JSON包装

        Args:
            response: 原始响应

        Returns:
            str: 清理后的纯文本响应
        """
        try:
            if not response:
                return ""

            text = response.strip()

            # 移除markdown代码块标记
            if text.startswith("```"):
                lines = text.split("\n")
                # 移除第一行（```json 或 ```）
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                # 移除最后一行（```）
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines).strip()

            # 尝试解析JSON
            if text.startswith("["):
                data = json.loads(text)
                if isinstance(data, list) and len(data) > 0:
                    first = data[0]
                    if isinstance(first, dict) and "answer" in first:
                        return first["answer"]
            elif text.startswith("{"):
                data = json.loads(text)
                if isinstance(data, dict) and "answer" in data:
                    return data["answer"]
                elif isinstance(data, dict) and "tasks" not in data:
                    return json.dumps(data, ensure_ascii=False, indent=2)

            return text
        except (json.JSONDecodeError, ValueError, KeyError):
            # 解析失败，返回原文（可能本来就是纯文本）
            return response.strip() if response else ""

    def _execute_automation_task(self, task_description: str, previous_results: str = "") -> Tuple[str, str]:
        """
        执行自动化任务
        
        Args:
            task_description: 任务描述
            previous_results: 前置步骤结果
            
        Returns:
            Tuple[str, str]: (执行结果, 状态)
        """
        try:
            # 填充prompt模板
            formatted_prompt = AUTOMATION_AGENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                task_description=task_description,
                previous_step_results=previous_results,
                tools=self.automation_agent.tool_registry.get_tools_description() if self.automation_agent.tool_registry else "暂无可用工具"
            )
            
            # 更新Agent的系统提示词
            self.automation_agent.system_prompt = formatted_prompt
            
            # 执行自动化任务
            response = self.automation_agent.run(input_text=task_description)
            # 清理响应，提取纯文本
            cleaned_response = self._clean_agent_response(response)
            return cleaned_response, "success"
        except Exception as e:
            logger.error(f"❌ 自动化任务执行失败: {str(e)}")
            return f"自动化执行失败: {str(e)}", "failed"

    def _aggregate_results(self, task_results: List[Dict[str, Any]]) -> str:
        """
        聚合所有任务结果，生成最终总结
        
        Args:
            task_results: 所有任务的执行结果
            
        Returns:
            str: 最终总结报告
        """
        if not task_results:
            return "未执行任何任务"
        
        summary = "## 任务执行总结\n\n"
        for i, result in enumerate(task_results, 1):
            status_icon = "✅" if result['status'] == 'success' else "❌"
            summary += f"### {i}. {result['task_description']}\n"
            summary += f"**状态**: {status_icon} {result['status']}\n"
            summary += f"**结果**: {result['execution_result']}\n\n"
            
            if result.get('output_file'):
                summary += f"**输出文件**: {result['output_file']}\n\n"
        
        return summary

    def _format_task_results_for_synthesis(self, task_results: List[Dict[str, Any]]) -> str:
        """把任务结果整理成适合二次总结的文本。"""
        if not task_results:
            return "暂无任务结果。"

        lines = []
        for item in task_results:
            step = item.get("step", "")
            agent_name = item.get("agent_name") or item.get("agent") or ""
            task_desc = item.get("task_description", "")
            status = item.get("status", "")
            result = item.get("result") or item.get("execution_result") or ""
            output_file = item.get("output_file")
            lines.append(f"- 步骤 {step} | {agent_name} | 状态: {status}")
            lines.append(f"  任务: {task_desc}")
            lines.append(f"  结果: {result}")
            if output_file:
                lines.append(f"  文件: {output_file}")
        return "\n".join(lines)

    def _synthesize_final_answer(
        self,
        query: str,
        task_results: List[Dict[str, Any]],
        conversation_history: str = "",
    ) -> str:
        """把子任务结果整理成面向用户的最终回答。"""
        try:
            results_text = self._format_task_results_for_synthesis(task_results)
            system_prompt = """
你是 Bio-Agent 的最终回答整理器。
你的任务是把任务结果整理成用户可直接阅读的最终回答。

要求：
1. 直接回答用户问题，不要输出任务清单或思考过程。
2. 优先使用任务结果中的事实，不要编造。
3. 如果包含联网检索结果，说明信息来自公开网页，并保留必要的不确定性。
4. 如果部分任务失败，只保留可用信息并简要说明局限。
5. 使用简洁中文，允许 Markdown。
""".strip()
            user_prompt = f"""用户问题：
{query}

对话历史：
{conversation_history or "无"}

子任务结果：
{results_text}
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = self.llm.invoke(messages, temperature=0.2, max_tokens=1200)
            cleaned = self._clean_agent_response(response)
            return cleaned or self._aggregate_results(task_results)
        except Exception as e:
            logger.warning(f"⚠️ 最终回答整理失败，回退到任务总结: {e}")
            return self._aggregate_results(task_results)

    def _classify_query(self, query: str) -> str:
        """
        判断用户问题应该走哪条路由。

        Args:
            query: 用户查询文本

        Returns:
            str: "local_qa"、"web_qa"、"action" 或 "mixed"
        """
        try:
            classify_prompt = QUERY_CLASSIFIER_PROMPT.format(user_request=query)
            messages = [
                {"role": "system", "content": classify_prompt},
                {"role": "user", "content": query}
            ]
            # 使用轻量级分类，不占用主 Agent 上下文
            response = self.llm.invoke(messages, temperature=0.0, max_tokens=12)
            result = response.strip().upper()
            logger.info(f"🔎 查询分类结果: {result} (query: {query[:30]}...)")
            for label in ("LOCAL_QA", "WEB_QA", "ACTION", "MIXED"):
                if label in result:
                    return label.lower()
            if "COMPLEX" in result:
                return "mixed"
            if "SIMPLE" in result:
                return "local_qa"
            return "mixed"
        except Exception as e:
            logger.warning(f"⚠️ 查询分类失败，默认走 MIXED 流程: {e}")
            return "mixed"

    def run(self, query: str, file_context: Optional[str] = None) -> str:
        """
        执行完整的用户请求处理流程
        
        Args:
            query: 用户查询文本
            file_context: 上传文件的内容（如果有）
            
        Returns:
            str: 最终响应
        """
        logger.info(f"🔍 收到用户请求: {query[:50]}..." if len(query) > 50 else f"🔍 收到用户请求: {query}")
        
        try:
            attachment_context = (file_context or "").strip()
            effective_query = query
            if attachment_context:
                effective_query = (
                    f"{query}\n\n"
                    "Uploaded attachment context for this turn:\n"
                    f"{attachment_context}"
                )

            # 0. 查询路由：纯知识、联网问答、单步执行直接处理，混合任务才交给主控拆解
            query_type = self._classify_query(effective_query)
            if query_type == "local_qa":
                logger.info("🟢 识别为本地知识问答，直接使用知识问答Agent回答")
                return self._execute_knowledge_task(effective_query)[0]
            if query_type == "web_qa":
                logger.info("🌐 识别为联网问答，直接使用 web_search 路径回答")
                return self._execute_web_qa_task(effective_query)[0]
            if query_type == "action":
                logger.info("🛠️ 识别为单步执行任务，直接使用自动化执行Agent处理")
                return self._execute_automation_task(effective_query)[0]

            # 1. 使用主控Agent进行任务分解（仅混合任务）
            logger.info("🔴 识别为混合任务，进入主控Agent任务分解")
            master_prompt = MASTER_AGENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                user_request=effective_query,
                conversation_history="无"
            )
            self.master_agent.system_prompt = master_prompt
            
            master_response = self.master_agent.run(input_text=effective_query)
            tasks = self._parse_master_response(master_response)
            
            if not tasks:
                # 如果解析失败，回退到 automation_agent，避免需要工具的问题被知识Agent拒答
                logger.info("⚠️ 主控Agent未返回有效任务列表，回退到自动化执行Agent直接处理")
                return self._execute_automation_task(effective_query)[0]
            
            logger.info(f"📋 主控Agent分解出 {len(tasks)} 个任务")
            
            # 2. 按顺序执行任务（考虑依赖关系）
            task_results: List[Dict[str, Any]] = []
            previous_results = ""
            
            for task in tasks:
                step = task.get('step', 0)
                agent = task.get('agent', '')
                task_desc = task.get('task_description', '')
                dependency = task.get('dependency')
                
                # 检查依赖是否已完成
                if isinstance(dependency, int) and dependency > len(task_results):
                    logger.warning(f"⚠️ 任务 {step} 依赖的步骤 {dependency} 尚未执行，跳过")
                    continue
                
                logger.info(f"🚀 执行任务 {step}: {task_desc[:30]}...")
                
                result, status = self._execute_task(task, previous_results)
                
                # 解析执行结果（如果是JSON格式）
                execution_result = result
                output_file = None
                try:
                    result_json = json.loads(result)
                    if isinstance(result_json, list) and len(result_json) > 0:
                        execution_result = result_json[0].get('execution_result', result)
                        output_file = result_json[0].get('output_file')
                        status = result_json[0].get('status', status)
                except json.JSONDecodeError:
                    pass
                
                task_results.append({
                    'step': step,
                    'agent': agent,
                    'task_description': task_desc,
                    'execution_result': execution_result,
                    'status': status,
                    'output_file': output_file
                })
                
                # 更新前置结果
                previous_results = execution_result
            
            # 3. 主控汇总子任务结果，生成最终回答
            final_summary = self._synthesize_final_answer(effective_query, task_results, "无")
            
            # 4. 保存任务历史
            self.task_history.append({
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'tasks': tasks,
                'results': task_results,
                'summary': final_summary
            })
            
            logger.info("✅ 请求处理完成")
            return final_summary
            
        except Exception as e:
            logger.error(f"❌ 请求处理失败: {str(e)}", exc_info=True)
            return f"处理请求时发生错误: {str(e)}"

    def run_research_stream(
        self,
        username: str,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        file_context: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        流式执行研究任务，支持任务清单实时更新和群聊效果

        Args:
            username: 用户名
            query: 用户查询文本
            history: 对话历史列表，每个元素包含 'role' 和 'content'

        Yields:
            Dict[str, Any]: 事件字典，包含任务状态更新和消息
        """
        try:
            attachment_context = (file_context or "").strip()
            effective_query = query
            if attachment_context:
                effective_query = (
                    f"{query}\n\n"
                    "Uploaded attachment context for this turn:\n"
                    f"{attachment_context}"
                )
            logger.info(f"🔍 用户 {username} 发起研究请求: {query[:50]}...")

            # 格式化对话历史
            history_str = self._format_history(history or [])
            if attachment_context:
                history_str = (
                    f"{history_str}\n\n"
                    "Uploaded attachment context for this turn:\n"
                    f"{attachment_context}"
                )

            # 0. 查询路由：纯知识、联网问答、单步执行直接处理，混合任务才分发给 master_agent
            query_type = self._classify_query(effective_query)
            if query_type == "local_qa":
                logger.info("🟢 识别为本地知识问答，直接使用知识问答Agent流式回答")
                yield {
                    'type': 'message',
                    'content': '让我来回答你的问题...',
                    'agent': 'knowledge_agent',
                    'agent_name': '知识问答专家'
                }
                for chunk in self._execute_knowledge_task_stream(effective_query, conversation_history=history_str):
                    yield {
                        'type': 'message_chunk',
                        'agent': 'knowledge_agent',
                        'agent_name': '知识问答专家',
                        'content': chunk,
                        'complete': False
                    }
                yield {'type': 'done'}
                return

            if query_type == "web_qa":
                logger.info("🌐 识别为联网问答，直接使用 web_search 路径流式回答")
                yield {
                    'type': 'message',
                    'content': '我先帮你查找最新公开信息...',
                    'agent': 'automation_agent',
                    'agent_name': '联网检索专家'
                }
                for chunk in self._execute_web_qa_task_stream(effective_query, conversation_history=history_str):
                    yield {
                        'type': 'message_chunk',
                        'agent': 'automation_agent',
                        'agent_name': '联网检索专家',
                        'content': chunk,
                        'complete': False
                    }
                yield {'type': 'done'}
                return

            if query_type == "action":
                logger.info("🛠️ 识别为单步执行任务，直接使用自动化执行Agent流式处理")
                yield {
                    'type': 'message',
                    'content': '我来直接处理这个任务...',
                    'agent': 'automation_agent',
                    'agent_name': '自动化执行专家'
                }
                for chunk in self._execute_automation_task_stream(effective_query):
                    yield {
                        'type': 'message_chunk',
                        'agent': 'automation_agent',
                        'agent_name': '自动化执行专家',
                        'content': chunk,
                        'complete': False
                    }
                yield {'type': 'done'}
                return

            # 1. 使用主控Agent进行任务分解（仅混合任务）
            logger.info("🔴 识别为混合任务，进入主控Agent任务分解")
            master_prompt = MASTER_AGENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                user_request=effective_query,
                conversation_history=history_str
            )
            self.master_agent.system_prompt = master_prompt

            master_response = self.master_agent.run(input_text=effective_query)
            tasks = self._parse_master_response(master_response)
            
            # 如果有任务，发送任务分解总结
            if tasks:
                task_descriptions = "\n".join([f"步骤 {t.get('step')}: {t.get('task_description')[:30]}..." for t in tasks])
                yield {
                    'type': 'message',
                    'content': f"\n我将按照以下步骤进行：\n{task_descriptions}",
                    'agent': 'master_agent',
                    'agent_name': '主控调度专家'
                }

            if not tasks:
                logger.info("⚠️ 主控 Agent 未返回有效任务列表，回退到自动化执行路径")
                yield {
                    'type': 'message',
                    'content': '我先直接处理这个问题...',
                    'agent': 'automation_agent',
                    'agent_name': '自动化执行专家'
                }

                for chunk in self._execute_automation_task_stream(effective_query):
                    yield {
                        'type': 'message_chunk',
                        'agent': 'automation_agent',
                        'agent_name': '自动化执行专家',
                        'content': chunk,
                        'complete': False
                    }
                yield {'type': 'done'}
                return

            # 2. 发送任务列表事件
            yield {'type': 'tasks', 'tasks': tasks}

            # 3. 按顺序执行任务
            previous_results = ""
            task_results = []  # 收集所有任务结果用于总结

            for task in tasks:
                step = task.get('step', 0)
                agent = task.get('agent', '')
                task_desc = task.get('task_description', '')
                dependency = task.get('dependency')

                # 检查依赖
                if isinstance(dependency, int) and dependency > len(task_results):
                    logger.warning(f"⚠️ 任务 {step} 依赖的步骤 {dependency} 尚未执行")
                    continue

                # 发送任务开始事件
                yield {'type': 'task_start', 'step': step, 'task': task}

                logger.info(f"🚀 执行任务 {step}: {task_desc[:30]}...")

                # 获取Agent名称（用于群聊显示）
                agent_name_map = {
                    'knowledge_agent': '知识问答专家',
                    'automation_agent': '自动化执行专家',
                    'master_agent': '主控调度专家'
                }
                current_agent_name = agent_name_map.get(agent, agent)

                try:
                    # 根据 Agent 类型选择流式执行方法
                    if agent == 'knowledge_agent':
                        # 流式执行知识问答任务
                        result = ""
                        for chunk in self._execute_knowledge_task_stream(task_desc, conversation_history=history_str):
                            result += chunk
                            yield {
                                'type': 'message_chunk',
                                'agent': agent,
                                'agent_name': current_agent_name,
                                'content': chunk,
                                'complete': False
                            }
                        # 标记完成
                        yield {
                            'type': 'message_chunk',
                            'agent': agent,
                            'agent_name': current_agent_name,
                            'content': '',
                            'complete': True
                        }
                        status = 'success'
                    elif agent == 'automation_agent':
                        # 流式执行自动化任务
                        result = ""
                        for chunk in self._execute_automation_task_stream(task_desc, previous_results):
                            result += chunk
                            yield {
                                'type': 'message_chunk',
                                'agent': agent,
                                'agent_name': current_agent_name,
                                'content': chunk,
                                'complete': False
                            }
                        # 标记完成
                        yield {
                            'type': 'message_chunk',
                            'agent': agent,
                            'agent_name': current_agent_name,
                            'content': '',
                            'complete': True
                        }
                        status = 'success'
                    else:
                        # 其他 Agent 使用原有方法
                        result, status = self._execute_task(task, previous_results)
                        yield {
                            'type': 'message',
                            'content': result,
                            'agent': agent,
                            'agent_name': current_agent_name
                        }

                    # 发送任务完成事件
                    yield {
                        'type': 'task_complete',
                        'step': step,
                        'result': result,
                        'status': status
                    }

                    # 收集任务结果用于总结
                    task_results.append({
                        'step': step,
                        'agent': agent,
                        'agent_name': current_agent_name,
                        'task_description': task_desc,
                        'result': result,
                        'status': status
                    })

                    previous_results = result

                except Exception as e:
                    logger.error(f"❌ 任务 {step} 执行失败: {str(e)}")
                    yield {
                        'type': 'task_error',
                        'step': step,
                        'error': str(e)
                    }
                    # 群聊效果：发送错误消息
                    yield {
                        'type': 'message',
                        'content': f"执行任务时出现错误: {str(e)}",
                        'agent': agent,
                        'agent_name': current_agent_name
                    }
                    # 收集失败结果用于总结
                    task_results.append({
                        'step': step,
                        'agent': agent,
                        'agent_name': current_agent_name,
                        'task_description': task_desc,
                        'result': str(e),
                        'status': 'failed'
                    })

            # 4. 主控汇总子任务结果，生成最终回答（流式）
            summary_content = self._synthesize_final_answer(effective_query, task_results, history_str)
            
            # 创建新消息
            yield {
                'type': 'message',
                'content': '',
                'agent': 'master_agent',
                'agent_name': '主控调度专家'
            }

            chunk_size = 20
            for i in range(0, len(summary_content), chunk_size):
                chunk = summary_content[i:i+chunk_size]
                complete = (i + chunk_size) >= len(summary_content)
                yield {
                    'type': 'message_chunk',
                    'agent': 'master_agent',
                    'agent_name': '主控调度专家',
                    'content': chunk,
                    'complete': complete
                }

            yield {'type': 'done'}

            logger.info("✅ 研究任务处理完成")

        except Exception as e:
            logger.error(f"❌ 研究任务失败: {str(e)}")
            yield {'type': 'error', 'detail': str(e)}

    def _execute_knowledge_task_stream(self, query: str, conversation_history: str = "") -> Iterator[str]:
        """
        流式执行知识问答任务（真正的流式输出，支持思考过程）

        Args:
            query: 用户问题
            conversation_history: 格式化的对话历史字符串

        Yields:
            str: 响应片段
        """
        try:
            rag_config = self.admin_config.get("rag", {})
            context = ""
            if rag_config.get("enabled", True):
                context = self.rag_service.build_context(
                    query=query,
                    namespace=rag_config.get("namespace", "default"),
                    top_k=int(rag_config.get("top_k", 5)),
                )

            # 填充 prompt 模板
            formatted_prompt = KNOWLEDGE_AGENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                query=query,
                conversation_history=conversation_history or "无",
                context=context or "未检索到相关内部知识库内容"
            )

            # 更新 Agent 的系统提示词
            self.knowledge_agent.system_prompt = formatted_prompt

            # 真正的流式执行 - 每收到一个chunk就立即yield
            buffer = ""
            in_thinking_section = False
            in_answer_section = False
            
            for chunk in self.knowledge_agent.stream_run(input_text=query):
                buffer += chunk
                
                # 检查是否进入思考过程部分
                if "## 思考过程" in buffer and not in_thinking_section and not in_answer_section:
                    in_thinking_section = True
                    # 移除 "## 思考过程" 标记
                    buffer = buffer.replace("## 思考过程", "")
                    continue
                
                # 检查是否进入回答部分
                if "## 回答" in buffer and in_thinking_section:
                    in_thinking_section = False
                    in_answer_section = True
                    # 移除 "## 回答" 标记
                    buffer = buffer.replace("## 回答", "")
                    continue
                
                # 流式输出思考过程或回答
                if len(buffer) >= 5:
                    # 找到最近的标点或空格位置进行分割
                    split_pos = buffer.rfind('。')
                    if split_pos == -1:
                        split_pos = buffer.rfind('？')
                    if split_pos == -1:
                        split_pos = buffer.rfind('！')
                    if split_pos == -1:
                        split_pos = buffer.rfind('\n')
                    if split_pos == -1:
                        split_pos = buffer.rfind(' ')
                    if split_pos == -1:
                        split_pos = len(buffer)
                    
                    # 安全检查：确保split_pos在有效范围内
                    if split_pos >= 0 and split_pos < len(buffer):
                        send_content = buffer[:split_pos+1] if buffer[split_pos] in '。？！' else buffer[:split_pos]
                        buffer = buffer[len(send_content):]
                    else:
                        send_content = buffer
                        buffer = ""
                    
                    if send_content.strip():
                        yield send_content
            
            # 发送剩余内容
            if buffer.strip():
                yield buffer

        except Exception as e:
            logger.error(f"❌ 知识问答任务执行失败：{str(e)}")
            yield f"问答失败：{str(e)}"

    def _execute_automation_task_stream(self, task_description: str, previous_results: str = "") -> Iterator[str]:
        """
        流式执行自动化任务（真正的流式输出，支持思考过程）

        Args:
            task_description: 任务描述
            previous_results: 前置步骤结果

        Yields:
            str: 响应片段
        """
        try:
            # 填充 prompt 模板
            formatted_prompt = AUTOMATION_AGENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                task_description=task_description,
                previous_step_results=previous_results,
                tools=self.automation_agent.tool_registry.get_tools_description() if self.automation_agent.tool_registry else "暂无可用工具"
            )

            # 更新 Agent 的系统提示词
            self.automation_agent.system_prompt = formatted_prompt

            # 流式收集完整响应
            buffer = ""
            in_thinking_section = False
            in_plan_section = False
            in_result_section = False
            
            for chunk in self.automation_agent.stream_run(input_text=task_description):
                buffer += chunk
                
                # 检查是否进入思考过程部分
                if "## 思考过程" in buffer and not in_thinking_section and not in_plan_section and not in_result_section:
                    in_thinking_section = True
                    # 移除 "## 思考过程" 标记
                    buffer = buffer.replace("## 思考过程", "")
                    continue
                
                # 检查是否进入执行计划部分
                if "## 执行计划" in buffer and in_thinking_section:
                    in_thinking_section = False
                    in_plan_section = True
                    # 移除 "## 执行计划" 标记
                    buffer = buffer.replace("## 执行计划", "")
                    continue
                
                # 检查是否进入执行结果部分
                if "## 执行结果" in buffer and in_plan_section:
                    in_plan_section = False
                    in_result_section = True
                    # 移除 "## 执行结果" 标记
                    buffer = buffer.replace("## 执行结果", "")
                    continue
                
                # 流式输出思考过程、执行计划或执行结果
                if len(buffer) >= 5:
                    # 找到最近的标点或空格位置进行分割
                    split_pos = buffer.rfind('。')
                    if split_pos == -1:
                        split_pos = buffer.rfind('？')
                    if split_pos == -1:
                        split_pos = buffer.rfind('！')
                    if split_pos == -1:
                        split_pos = buffer.rfind('\n')
                    if split_pos == -1:
                        split_pos = buffer.rfind(' ')
                    if split_pos == -1:
                        split_pos = len(buffer)
                    
                    # 安全检查：确保split_pos在有效范围内
                    if split_pos >= 0 and split_pos < len(buffer):
                        send_content = buffer[:split_pos+1] if buffer[split_pos] in '。？！' else buffer[:split_pos]
                        buffer = buffer[len(send_content):]
                    else:
                        send_content = buffer
                        buffer = ""
                    
                    if send_content.strip():
                        yield send_content
            
            # 发送剩余内容
            if buffer.strip():
                yield buffer
            
        except Exception as e:
            logger.error(f"❌ 自动化任务执行失败：{str(e)}")
            yield f"自动化执行失败：{str(e)}"


    def add_rag_text(self, text: str, source: str = "text", namespace: str = "default") -> int:
        """添加文本到 RAG 知识库。"""
        return self.rag_service.add_text(text=text, source=source, namespace=namespace)

    def add_rag_file(self, file_path: str, namespace: str = "default") -> int:
        """添加本地文件到 RAG 知识库。"""
        return self.rag_service.add_file(file_path=file_path, namespace=namespace)

    def add_rag_upload(self, file: Any, namespace: str = "default") -> int:
        """添加上传文件到 RAG 知识库。"""
        return self.rag_service.add_upload(file=file, namespace=namespace)

    def parse_upload(self, file: Any) -> str:
        """Parse an uploaded file without indexing it into the RAG store."""
        filename = file.filename or "attachment.txt"
        suffix = Path(filename).suffix.lower() or ".txt"
        if hasattr(file.file, "seek"):
            file.file.seek(0)
        return self.rag_service._load_upload(file=file, suffix=suffix)

    def list_rag_documents(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """列出 RAG 文档。"""
        return self.rag_service.list_documents(namespace=namespace)

    def set_rag_document_status(self, source: str, namespace: str = "default", status: str = "active") -> int:
        """启用或停用 RAG 文档。"""
        return self.rag_service.set_document_status(source=source, namespace=namespace, status=status)

    def delete_rag_document(self, source: str, namespace: str = "default") -> int:
        """删除 RAG 文档。"""
        return self.rag_service.delete_document(source=source, namespace=namespace)

    def search_rag(self, query: str, namespace: str = "default", top_k: int = 5) -> List[Dict[str, Any]]:
        """检索 RAG 知识库。"""
        return self.rag_service.search(query=query, namespace=namespace, top_k=top_k)

    def get_rag_stats(self) -> Dict[str, Any]:
        """获取 RAG 知识库统计信息。"""
        return self.rag_service.stats()

    def execute_automation(self, task_description: str, previous_results: str = "") -> str:
        """
        直接执行自动化任务
        
        Args:
            task_description: 任务描述
            previous_results: 前置步骤结果
            
        Returns:
            str: 执行结果
        """
        result, status = self._execute_automation_task(task_description, previous_results)
        return result

    def _generate_summary(self, query: str, tasks: List[Dict], task_results: List[Dict]) -> str:
        """
        生成任务执行总结报告
        
        Args:
            query: 用户原始问题
            tasks: 任务列表
            task_results: 任务执行结果列表
            
        Returns:
            str: 总结报告内容
        """
        # 统计成功和失败的任务
        success_count = sum(1 for r in task_results if r.get('status') == 'success')
        fail_count = len(task_results) - success_count
        
        # 构建总结报告
        summary_parts = []
        
        # 开头
        summary_parts.append(f"根据您的问题「{query}」，我已完成以下分析：")
        
        # 任务执行概况
        summary_parts.append(f"\n📊 任务执行概况：")
        summary_parts.append(f"   - 共执行 {len(task_results)} 个步骤")
        summary_parts.append(f"   - ✅ 成功：{success_count} 个")
        if fail_count > 0:
            summary_parts.append(f"   - ❌ 失败：{fail_count} 个")
        
        # 各步骤详情
        if task_results:
            summary_parts.append(f"\n📋 各步骤执行详情：")
            for result in task_results:
                step = result.get('step', 0)
                agent_name = result.get('agent_name', '')
                task_desc = result.get('task_description', '')[:50] + "..." if len(result.get('task_description', '')) > 50 else result.get('task_description', '')
                status = result.get('status', '')
                result_content = result.get('result', '')
                
                status_icon = "✅" if status == 'success' else "❌"
                summary_parts.append(f"\n{status_icon} **步骤 {step}**（{agent_name}）")
                summary_parts.append(f"   任务：{task_desc}")
                
                # 如果是成功的任务，提取关键结果
                if status == 'success':
                    # 清理结果内容，提取关键信息
                    clean_result = self._clean_summary_result(result_content)
                    if clean_result and len(clean_result) > 0:
                        summary_parts.append(f"   结果：{clean_result}")
                else:
                    summary_parts.append(f"   错误：{result_content[:100]}...")
        
        # 总结
        summary_parts.append(f"\n🎯 总结：")
        if fail_count == 0:
            summary_parts.append("   所有任务均已成功完成！")
        else:
            summary_parts.append(f"   部分任务执行失败（{fail_count}/{len(task_results)}），请查看详情。")
        
        summary_parts.append("\n如果您需要进一步的帮助或有其他问题，请随时告诉我！")
        
        return "\n".join(summary_parts)

    def _clean_summary_result(self, result: str) -> str:
        """
        清理任务结果，提取关键信息用于总结
        
        Args:
            result: 原始任务结果
            
        Returns:
            str: 清理后的结果摘要
        """
        if not result:
            return ""
            
        # 移除JSON格式
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
            if cleaned.lower().startswith('json'):
                cleaned = cleaned[4:].strip()
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3].strip()
        
        # 尝试解析JSON提取关键信息
        try:
            data = json.loads(cleaned)
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                if isinstance(item, dict):
                    # 提取关键字段
                    if 'execution_result' in item:
                        return item['execution_result'][:100] + "..." if len(item['execution_result']) > 100 else item['execution_result']
                    elif 'answer' in item:
                        return item['answer'][:100] + "..." if len(item['answer']) > 100 else item['answer']
                    elif 'result' in item:
                        return str(item['result'])[:100] + "..." if len(str(item['result'])) > 100 else str(item['result'])
        except:
            pass
        
        # 如果不是JSON或者解析失败，直接截取文本
        # 移除多余的空白和特殊字符
        cleaned = ' '.join(cleaned.split())
        if len(cleaned) > 150:
            cleaned = cleaned[:150] + "..."
        
        return cleaned

    def call_mcp_service(self, service_name: str, **kwargs) -> str:
        """
        调用MCP服务
        
        Args:
            service_name: MCP服务名称
            **kwargs: 服务参数
            
        Returns:
            str: 服务响应
        """
        if service_name not in self.mcp_services:
            return f"未找到MCP服务: {service_name}"
        
        try:
            mcp_tool = self.mcp_services[service_name]['tool']
            result = mcp_tool.run(kwargs)
            return f"MCP服务 '{service_name}' 执行成功:\n{result}"
        except Exception as e:
            logger.error(f"❌ MCP服务调用失败: {str(e)}")
            return f"MCP服务调用失败: {str(e)}"

    def write_and_run_script(self, script_content: str, script_type: str = "python") -> str:
        """
        编写并执行脚本
        
        Args:
            script_content: 脚本内容
            script_type: 脚本类型 (python/bash)
            
        Returns:
            str: 执行结果
        """
        try:
            import subprocess
            import tempfile
            import os
            
            # 创建临时脚本文件
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{script_type}', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            # 执行脚本
            if script_type == "python":
                result = subprocess.run(
                    ['python', script_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            elif script_type == "bash":
                result = subprocess.run(
                    ['bash', script_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            else:
                return f"不支持的脚本类型: {script_type}"
            
            # 清理临时文件
            os.unlink(script_path)
            
            if result.returncode == 0:
                return f"脚本执行成功:\n{result.stdout}"
            else:
                return f"脚本执行失败:\n标准输出: {result.stdout}\n错误输出: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "脚本执行超时"
        except Exception as e:
            logger.error(f"❌ 脚本执行失败: {str(e)}")
            return f"脚本执行失败: {str(e)}"

    def parse_document(self, file_path: str) -> str:
        """
        解析文档文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 解析结果
        """
        try:
            file_ext = file_path.split('.')[-1].lower()
            
            if file_ext not in self.supported_file_types:
                return f"不支持的文件类型: {file_ext}"
            
            if file_ext == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_ext == 'pdf':
                # PDF解析（需要安装PyPDF2或pdfplumber）
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = "\n".join(page.extract_text() for page in reader.pages)
                        return text
                except ImportError:
                    return "需要安装PyPDF2库来解析PDF文件"
            elif file_ext in ['json', 'csv']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_ext in ['fasta', 'genbank']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 可以添加生物信息学格式的解析逻辑
                    return content
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
                    
        except FileNotFoundError:
            return f"文件未找到: {file_path}"
        except Exception as e:
            logger.error(f"❌ 文档解析失败: {str(e)}")
            return f"文档解析失败: {str(e)}"

    def list_mcp_services(self) -> List[Dict[str, str]]:
        """
        获取已注册的MCP服务列表
        
        Returns:
            List[Dict]: 服务列表
        """
        return [
            {'name': name, 'description': info['description']}
            for name, info in self.mcp_services.items()
        ]

    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取任务执行历史
        
        Args:
            limit: 返回条数限制
            
        Returns:
            List[Dict]: 任务历史列表
        """
        return self.task_history[-limit:]

    def clear_history(self) -> None:
        """清空任务历史"""
        self.task_history.clear()
        self.master_agent.clear_history()
        self.knowledge_agent.clear_history()
        self.automation_agent.clear_history()

    def __str__(self) -> str:
        return f"BioAgent(mcp_services={len(self.mcp_services)}, tasks_executed={len(self.task_history)})"

    def __repr__(self) -> str:
        return self.__str__()
