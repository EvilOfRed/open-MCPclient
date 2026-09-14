# MCP Client · 智能代理

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 **Model Context Protocol (MCP)** 的客户端实现，能够连接多个 MCP 服务端，将它们的工具（Tools）暴露给大语言模型（LLM），实现复杂的自动化任务。支持流式推理、工具调用、多轮对话持久化，并提供 RPC 接口供外部程序调用（为高度自定义的流程化调用提供支持）。

---

## 特性

- 🧩 **多服务聚合** – 同时连接多个 stdio 类型的 MCP 服务端，自动合并所有工具。
- 🤖 **LLM 驱动** – 通过 OpenAI 兼容的 API（支持推理模型），自动选择并调用合适的工具。
- 🧠 **推理过程保留** – 支持 `reasoning_content` 的流式展示与存储（如 DeepSeek R1 系列）。
- 💾 **对话持久化** – 每次会话自动保存完整消息历史（含工具调用结果），支持断点续聊。
- 🖼️ **多模态支持** – 支持 Base64 图片输入（自动识别格式），可结合视觉模型。
- 🔌 **RPC 接口** – 提供简单的 JSON-RPC 服务，允许外部进程控制对话（查询层数、切换会话等）。
- 📦 **轻量配置** – 通过 JSON 文件配置 MCP 服务端列表，环境变量管理密钥。

---


## 开始方法

### 1. 安装依赖

```bash
pip install mcp openai python-dotenv mcp_rpc_utils
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件，填入以下内容：

env
MCP_BASE_URL=你的模型基础路径
MCP_API_KEY=你的API密钥
MCP_MODEL=你的模型名称


- `MCP_BASE_URL`：OpenAI 兼容 API 的基础地址（如官方、DeepSeek、本地代理等）。
- `MCP_API_KEY`：对应的 API Key。
- `MCP_MODEL`：要使用的模型名称，例如 `gpt-4o`、`deepseek-chat` 等。

> 注意：`client.py` 中的 `config_path` 默认指向 `C:\mcp_server\config\serverPaths.json`，以及系统提示词 `C:/mcp_server/sysprompt/ServiceCode.md`。请根据实际路径修改，或把对应文件放到该位置。

### 3. 交互式聊天

直接运行 `client.py`：

```bash
python client.py
```


## 配置 MCP 服务端
在 config/serverPaths.json（路径可修改）中定义服务端列表，例如：

```json
{
  "mcpServers": {
    "filesystem": {
      "type": "stdio",
      "command": "python",
      "args": ["filesystem_server.py"]
    },
    "weather": {
      "type": "stdio",
      "command": "python",
      "args": ["weather_server.py"]
    }
  }
}
```
*尚不支持其它命令的启动形式。*

