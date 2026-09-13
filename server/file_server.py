
import mcp
from mcp.server import MCPServer
import subprocess
import time
import json
import os
from typing import Annotated
from pydantic import Field
from pathlib import Path

mcp = MCPServer("FILE_MCP")

@mcp.tool(name="mkdir", description="创建目录")  
def mkdir(path: Annotated[Path, Field(description="目录路径")]) -> str:
    """创建目录"""
    os.makedirs(path, exist_ok=True)
    return f"目录已创建：{path}"

@mcp.tool(name="list_files", description="列出目录下的所有文件") 
def list_files(path: Annotated[Path, Field(description="目录路径")]) -> str:
    """列出目录下的所有文件"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"目录不存在：{path}")
    files = os.listdir(path)
    return f"目录 {path} 下的文件列表：{files}"

@mcp.tool(name="read_file", description="读取指定文件的内容")
def read_file(file_path: Annotated[Path, Field(description="文件路径")]) -> str:
    """读取指定文件的内容"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

@mcp.tool(name="write_file", description="将内容写入指定文件,支持覆盖和追加写入模式,自动创建目录")
def write_file(
    file_path: Annotated[Path, Field(description="文件路径")], 
    content: Annotated[str, Field(description="要写入的内容")],
    write_mode: Annotated[str, Field(default="w", description="写入模式，'w'表示覆盖写入，'a'表示追加写入")] = "w"
) -> str:
    """将内容写入指定文件"""
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, write_mode, encoding='utf-8') as file:
        file.write(content)
    return f"文件已写入：{file_path}"

@mcp.tool(name="open_folder", description="在文件资源管理器中打开指定文件夹")
def open_folder(path: Annotated[Path, Field(description="文件夹路径")]) -> str:
    """在文件资源管理器中打开指定文件夹"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件夹不存在：{path}")
    subprocess.run(["explorer", path])
    return f"文件夹已打开：{path}"

@mcp.tool(name="check_path", description="检查指定路径（文件或目录）是否存在")
def check_path(path: Annotated[Path, Field(description="要检查的路径")]) -> str:
    """检查路径是否存在，返回状态信息"""
    if os.path.exists(path):
        return f"{path}路径存在。"
    else:
        return f"{path}路径不存在。"

if __name__ == "__main__": 
    mcp.run()
