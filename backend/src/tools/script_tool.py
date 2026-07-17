"""Safe Python script execution tool for data analysis tasks."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .base import Tool, ToolParameter


class PythonScriptTool(Tool):
    """Run a Python script in the configured workspace."""

    def __init__(self, workspace: str):
        super().__init__(
            name="python_script",
            description=(
                "执行用于数据处理、表格统计和可视化生成的 Python 脚本。"
                "脚本会在当前会话输出目录中运行，生成的文件应写入 output_dir。"
            ),
        )
        self.workspace = Path(workspace).resolve()
        self.output_dir = self.workspace
        self.python_executable = Path("/nfsdata/userHome/huanghong/anaconda3/envs/mlflow/bin/python")

    def set_output_dir(self, output_dir: str) -> None:
        target = Path(output_dir).resolve()
        target.mkdir(parents=True, exist_ok=True)
        self.output_dir = target

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="script",
                type="string",
                description="要执行的完整 Python 脚本源码。必须把输出文件写入 output_dir。",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        script = str(parameters.get("script") or parameters.get("input") or "").strip()
        if not script:
            return "错误：必须提供 script 参数"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["BIO_AGENT_OUTPUT_DIR"] = str(self.output_dir)
        env["BIO_AGENT_WORKSPACE"] = str(self.workspace)
        env.setdefault("MPLBACKEND", "Agg")

        if not self.python_executable.exists():
            return f"错误：未找到 mlflow conda 环境 Python：{self.python_executable}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        script_path = self.output_dir / f"executed_script_{timestamp}.py"
        script_path.write_text(script, encoding="utf-8")

        try:
            result = subprocess.run(
                [str(self.python_executable), str(script_path)],
                cwd=str(self.output_dir),
                env=env,
                text=True,
                capture_output=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return f"错误：Python 脚本执行超时\n解释器：{self.python_executable}\n脚本文件：{script_path}"

        output_parts = []
        if result.stdout.strip():
            output_parts.append(f"stdout:\n{result.stdout.strip()}")
        if result.stderr.strip():
            output_parts.append(f"stderr:\n{result.stderr.strip()}")
        output = "\n\n".join(output_parts) or "脚本未输出文本。"
        status = "成功" if result.returncode == 0 else f"失败，退出码 {result.returncode}"
        return (
            f"Python 脚本执行{status}\n"
            f"解释器：{self.python_executable}\n"
            f"脚本文件：{script_path}\n"
            f"输出目录：{self.output_dir}\n\n"
            f"{output}"
        )


def create_python_script_tool(workspace: str) -> PythonScriptTool:
    return PythonScriptTool(workspace=workspace)
