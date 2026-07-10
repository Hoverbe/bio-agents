"""
终端操控工具 - 提供安全的命令行执行能力

安全机制：
1. 命令白名单：只允许安全的只读命令
2. 工作目录限制（沙箱）：只能在指定工作目录内操作
3. 超时控制：每个命令都有执行时间限制
4. 输出大小限制：防止内存溢出
5. 跨平台兼容：自动识别Windows和Linux系统
"""

import os
import sys
import platform
import subprocess
import shlex
import shutil
from typing import Dict, Any, List
from pathlib import Path

from .base import Tool, ToolParameter


# ==================== 命令白名单 ====================

# Linux/Unix 系统的安全只读命令
LINUX_ALLOWED_COMMANDS = {
    # 文件列表与信息
    'ls', 'dir', 'tree',
    # 文件内容查看
    'cat', 'head', 'tail', 'less', 'more',
    # 文件搜索
    'find', 'grep', 'egrep', 'fgrep',
    # 文本处理
    'wc', 'sort', 'uniq', 'cut', 'awk', 'sed',
    # 目录操作
    'pwd', 'cd',
    # 文件信息
    'file', 'stat', 'du', 'df',
    # 其他
    'echo', 'which', 'whereis',
}

# Windows 系统的安全只读命令
WINDOWS_ALLOWED_COMMANDS = {
    # 文件列表与信息
    'dir', 'tree',
    # 文件内容查看
    'type', 'more',
    # 文件搜索
    'findstr', 'where',
    # 文本处理
    'sort',
    # 目录操作
    'cd', 'chdir', 'pushd', 'popd',
    # 文件信息
    'attrib', 'df', 'wmic',
    # 其他
    'echo', 'ver', 'systeminfo',
}

# 危险的命令模式（即使在白名单内也要拒绝）
DANGEROUS_PATTERNS = [
    'rm ', 'rm\t', 'rmdir', 'del ', 'rd ', 'remove',
    'mv ', 'move', 'rename', 'ren ',
    'cp ', 'copy', 'xcopy', 'robocopy',
    'chmod', 'chown', 'chgrp',
    'mkfs', 'format', 'fdisk', 'diskpart',
    'dd ', 'dd\t',
    'shutdown', 'reboot', 'poweroff', 'halt', 'init ',
    'kill ', 'killall', 'taskkill', 'taskkill /f',
    'sudo', 'su ',
    '>', '>>', '>|',  # 输出重定向
    '|',  # 管道（可执行任意命令）
    '`', '$(',
    'wget', 'curl',  # 网络下载
    'ssh', 'scp', 'ftp', 'telnet',
    'nc ', 'netcat', 'ncat',
    'eval', 'exec',
    'crontab', 'at ', 'batch',
    'useradd', 'userdel', 'usermod', 'groupadd', 'groupdel',
    'passwd', 'net user',  # 密码/用户管理
    'reg ', 'regedit',  # 注册表
    'sc ',  # 服务管理
    'net start', 'net stop',
    'bcdedit', 'bootrec',
    'cipher /w',  # 安全擦除
    'takeown', 'icacls',  # 权限管理
]


class TerminalTool(Tool):
    """
    终端操控工具 - 提供安全的命令行执行能力

    安全特性：
    1. 命令白名单：只允许安全的只读命令
    2. 工作目录沙箱：限制访问范围
    3. 超时控制：防止无限循环
    4. 输出大小限制：防止内存溢出
    5. 跨平台兼容：自动识别Windows和Linux
    """

    def __init__(
        self,
        name: str = "terminal",
        description: str = "在安全工作目录内执行命令行操作",
        workspace: str = ".",
        max_output_size: int = 10 * 1024 * 1024,  # 默认10MB
        timeout: int = 30  # 默认30秒
    ):
        """
        初始化终端工具

        Args:
            name: 工具名称
            description: 工具描述
            workspace: 工作目录（沙箱根目录）
            max_output_size: 最大输出大小（字节）
            timeout: 命令执行超时时间（秒）
        """
        super().__init__(name, description)
        self.os_type = self._detect_os()
        self.allowed_commands = self._get_allowed_commands()
        self.workspace = self._resolve_workspace(workspace)
        self.current_dir = self.workspace
        self.max_output_size = max_output_size
        self.timeout = timeout
        self._print_init_info()

    def _detect_os(self) -> str:
        """
        自动检测部署的系统类型

        Returns:
            str: "windows" 或 "linux"
        """
        system = platform.system().lower()
        if system == 'windows':
            return 'windows'
        elif system in ('linux', 'darwin', 'unix'):
            return 'linux'
        else:
            # 默认为linux
            return 'linux'

    def _get_allowed_commands(self) -> set:
        """
        根据系统类型获取对应的命令白名单

        Returns:
            set: 允许执行的命令集合
        """
        if self.os_type == 'windows':
            return WINDOWS_ALLOWED_COMMANDS.copy()
        return LINUX_ALLOWED_COMMANDS.copy()

    def _resolve_workspace(self, workspace: str) -> Path:
        """
        解析工作目录路径

        Args:
            workspace: 工作目录字符串

        Returns:
            Path: 解析后的绝对路径
        """
        path = Path(workspace).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _print_init_info(self):
        """打印初始化信息"""
        print(f"🖥️  TerminalTool 初始化完成")
        print(f"   系统类型: {self.os_type.upper()}")
        print(f"   工作目录: {self.workspace}")
        print(f"   超时时间: {self.timeout}秒")
        print(f"   最大输出: {self.max_output_size // 1024}KB")
        print(f"   允许命令数: {len(self.allowed_commands)}")

    def _parse_command(self, command: str) -> str:
        """
        解析命令，提取主命令名

        Args:
            command: 完整命令字符串

        Returns:
            str: 主命令名（小写）
        """
        command = command.strip()
        if not command:
            return ""

        # 跳过环境变量赋值（如 VAR=value command）
        while '=' in command and not command.startswith('/'):
            parts = command.split(None, 1)
            if len(parts) < 2 or '=' not in parts[0]:
                break
            command = parts[1]
            if not command:
                return ""

        # 解析第一个词作为命令名
        if self.os_type == 'windows':
            # Windows: 跳过路径分隔符
            parts = command.split()
            if not parts:
                return ""
            cmd_name = parts[0]
            # 移除扩展名（.exe, .cmd, .bat等）
            for ext in ['.exe', '.cmd', '.bat', '.ps1', '.com']:
                if cmd_name.lower().endswith(ext):
                    cmd_name = cmd_name[:-len(ext)]
                    break
            return cmd_name.lower()
        else:
            # Linux: 提取 basename
            cmd_name = os.path.basename(command.split()[0]) if command.split() else ""
            return cmd_name.lower()

    def _check_command_safety(self, command: str) -> tuple:
        """
        检查命令安全性

        Args:
            command: 要执行的命令

        Returns:
            tuple: (is_safe, error_message)
        """
        if not command or not command.strip():
            return False, "❌ 错误：命令不能为空"

        # 检查危险模式
        command_lower = command.lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in command_lower:
                return False, (
                    f"❌ 不允许的命令模式: '{pattern}'\n"
                    f"出于安全考虑，包含此模式的命令被拒绝执行。\n"
                    f"该工具仅支持安全的只读操作。"
                )

        # 检查主命令是否在白名单中
        cmd_name = self._parse_command(command)
        if not cmd_name:
            return False, "❌ 错误：无法解析命令"

        if cmd_name not in self.allowed_commands:
            return False, (
                f"❌ 不允许的命令: {cmd_name}\n"
                f"允许的命令: {', '.join(sorted(self.allowed_commands))}"
            )

        return True, ""

    def _check_path_safety(self, command: str) -> tuple:
        """
        检查命令中的路径是否在工作目录内

        Args:
            command: 要执行的命令

        Returns:
            tuple: (is_safe, error_message)
        """
        try:
            # 解析命令参数
            if self.os_type == 'windows':
                # Windows命令可能包含引号和特殊字符，简单处理
                args = command.split()
            else:
                # Linux使用shlex
                args = shlex.split(command)

            workspace_str = str(self.workspace)

            for arg in args[1:]:  # 跳过命令名
                if not arg or arg.startswith('-'):
                    continue

                # 处理 cd 命令
                if self._parse_command(command) in ('cd', 'chdir'):
                    target = arg
                    try:
                        # 解析目标路径（相对于当前目录或工作目录）
                        if os.path.isabs(target):
                            target_path = Path(target).resolve()
                        else:
                            target_path = (self.current_dir / target).resolve()

                        # 检查是否在工作目录内
                        target_str = str(target_path)
                        if not (target_str.startswith(workspace_str) or
                                target_str == workspace_str):
                            return False, (
                                f"❌ 不允许访问工作目录外的路径: {arg}\n"
                                f"工作目录: {self.workspace}"
                            )
                    except Exception:
                        pass
                    continue

                # 检查绝对路径
                if os.path.isabs(arg):
                    abs_path = Path(arg).resolve()
                    abs_str = str(abs_path)
                    if not (abs_str.startswith(workspace_str) or
                            abs_str == workspace_str):
                        return False, (
                            f"❌ 不允许访问工作目录外的路径: {arg}\n"
                            f"工作目录: {self.workspace}"
                        )

                # 检查通过 .. 逃逸的相对路径
                if '..' in arg:
                    try:
                        resolved = (self.current_dir / arg).resolve()
                        resolved_str = str(resolved)
                        if not (resolved_str.startswith(workspace_str) or
                                resolved_str == workspace_str):
                            return False, (
                                f"❌ 不允许访问工作目录外的路径: {arg}\n"
                                f"工作目录: {self.workspace}"
                            )
                    except Exception:
                        pass

            return True, ""

        except Exception as e:
            # 解析失败时默认拒绝
            return False, f"❌ 路径检查失败: {str(e)}"

    def _execute_command(self, command: str) -> str:
        """
        执行命令

        Args:
            command: 要执行的命令

        Returns:
            str: 命令执行结果
        """
        try:
            # 在当前目录下执行命令
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.current_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy()
            )

            # 合并标准输出和标准错误
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"

            # 检查输出大小
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size]
                output += f"\n\n⚠️ 输出被截断（超过 {self.max_output_size} 字节）"

            # 添加返回码信息
            if result.returncode != 0:
                output = f"⚠️ 命令返回码: {result.returncode}\n\n{output}"

            return output if output else "✅ 命令执行成功（无输出）"

        except subprocess.TimeoutExpired:
            return f"❌ 命令执行超时（超过 {self.timeout} 秒）"
        except Exception as e:
            return f"❌ 命令执行失败: {e}"

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行终端命令

        Args:
            parameters: 参数字典
                - command: 要执行的命令（必需）
                - action: 操作类型（可选: run/cd/pwd/ls）

        Returns:
            str: 执行结果
        """
        command = parameters.get("command", "").strip()
        action = parameters.get("action", "run").strip().lower()

        # 特殊操作处理
        if action == "pwd":
            return f"📍 当前工作目录: {self.current_dir}\n📁 工作空间根目录: {self.workspace}"

        if action == "info":
            return (
                f"🖥️  TerminalTool 信息\n"
                f"   系统类型: {self.os_type.upper()}\n"
                f"   工作目录: {self.workspace}\n"
                f"   当前目录: {self.current_dir}\n"
                f"   超时时间: {self.timeout}秒\n"
                f"   最大输出: {self.max_output_size // 1024}KB\n"
                f"   允许命令数: {len(self.allowed_commands)}\n"
                f"\n📋 允许的命令:\n{', '.join(sorted(self.allowed_commands))}"
            )

        if action == "help":
            return (
                "📖 TerminalTool 使用说明\n\n"
                "可用操作：\n"
                "  - run: 执行命令（默认）\n"
                "  - pwd: 查看当前工作目录\n"
                "  - info: 查看工具信息\n"
                "  - help: 查看帮助\n\n"
                "使用示例：\n"
                '  {"action": "run", "command": "ls -la"}\n'
                '  {"action": "pwd"}\n'
                '  {"action": "info"}'
            )

        # 执行命令前的安全检查
        if not command:
            return "❌ 错误：请提供要执行的命令"

        if self.os_type == 'windows' and command.lower() == 'df -h':
            command = 'wmic logicaldisk get caption,freespace,size'

        # 第一层：命令白名单检查
        is_safe, error_msg = self._check_command_safety(command)
        if not is_safe:
            return error_msg

        # 第二层：工作目录限制检查
        is_safe, error_msg = self._check_path_safety(command)
        if not is_safe:
            return error_msg

        # 如果是 cd 命令，更新当前目录
        cmd_name = self._parse_command(command)
        if cmd_name in ('cd', 'chdir'):
            return self._handle_cd_command(command)

        # 第三层 & 第四层：执行命令（已内置超时和输出限制）
        return self._execute_command(command)

    def _handle_cd_command(self, command: str) -> str:
        """
        处理 cd 命令，更新当前工作目录

        Args:
            command: cd 命令字符串

        Returns:
            str: 执行结果
        """
        try:
            if self.os_type == 'windows':
                parts = command.split()
            else:
                parts = shlex.split(command)

            if len(parts) == 1:
                # cd 无参数，回到工作空间根目录
                self.current_dir = self.workspace
                return f"📁 已切换到工作空间根目录: {self.current_dir}"

            target = parts[1]
            if os.path.isabs(target):
                new_dir = Path(target).resolve()
            else:
                new_dir = (self.current_dir / target).resolve()

            # 安全检查
            new_str = str(new_dir)
            workspace_str = str(self.workspace)
            if not (new_str.startswith(workspace_str) or new_str == workspace_str):
                return f"❌ 不允许访问工作目录外的路径: {target}"

            if not new_dir.exists():
                return f"❌ 目录不存在: {target}"

            if not new_dir.is_dir():
                return f"❌ 不是目录: {target}"

            self.current_dir = new_dir
            return f"📁 已切换到: {self.current_dir}"

        except Exception as e:
            return f"❌ cd 命令执行失败: {str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        """
        获取工具参数定义

        Returns:
            List[ToolParameter]: 参数定义列表
        """
        return [
            ToolParameter(
                name="command",
                type="string",
                description="要执行的命令，例如：ls -la, cat README.md, pwd",
                required=False,
                default=""
            ),
            ToolParameter(
                name="action",
                type="string",
                description="操作类型：run(执行命令)、pwd(查看当前目录)、info(查看工具信息)、help(查看帮助)",
                required=False,
                default="run"
            )
        ]


# ==================== 工厂函数 ====================

def create_terminal_tool(
    workspace: str = ".",
    max_output_size: int = 10 * 1024 * 1024,
    timeout: int = 30
) -> TerminalTool:
    """
    工厂函数：创建TerminalTool实例

    Args:
        workspace: 工作目录
        max_output_size: 最大输出大小（字节）
        timeout: 超时时间（秒）

    Returns:
        TerminalTool: 工具实例
    """
    return TerminalTool(
        workspace=workspace,
        max_output_size=max_output_size,
        timeout=timeout
    )
