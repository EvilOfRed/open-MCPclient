import json
import sys
import os
import contextlib
import re
import asyncio
from pathlib import Path
from datetime import datetime
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from openai import AsyncOpenAI
from typing import List, Tuple, Optional, Dict,Any
import inspect
from contextlib import AsyncExitStack
import uuid
import traceback
import base64
from dotenv import load_dotenv
load_dotenv()

class MCPClient:
    def __init__(self, base_url,api_key,config_path,model):
        self.llm_client=AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.server_config_path=config_path  # Path to the server script (.py or .js)
        self.available_tools=[]
        self.sessions=[]
        self.model=model
        self.messagesId=None
        self.layer=0
        self.preserve_thinking=True  
        self.preserve_messagesId=None

    async def _stream_response(self, stream) -> Tuple[str, Optional[List[Dict]], str]:
        """
        处理流式响应，实时打印内容，返回完整文本和工具调用信息（如果有）
        """
        collected_content = []
        tool_calls_dict = {}  # 用于合并多个工具调用的增量（index 作为键）
        collected_reasoning = []    
        finish_reason = None
        try:
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    print("*无效的 chunk，跳过...")
                    continue
                delta = choice.delta
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_text = delta.reasoning_content
                    # 为了区分，可以在输出时添加特殊标记，比如颜色或前缀
                    sys.stdout.write(f"\033[90m{reasoning_text}\033[0m")  # 灰色显示
                    sys.stdout.flush()
                    collected_reasoning.append(reasoning_text)
                # 处理内容增量
                if delta.content:
                    chunk_text = delta.content
                    sys.stdout.write(chunk_text)
                    sys.stdout.flush()
                    collected_content.append(chunk_text)

                # 处理工具调用增量（可能跨多个 chunk）
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_dict:
                            # 初始化工具调用条目
                            tool_calls_dict[idx] = {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": "",
                                    "arguments": ""
                                }
                            }
                        # 合并 name 和 arguments（arguments 是逐步拼接的）
                        if tc.function.name:
                            tool_calls_dict[idx]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments

                # 记录 finish_reason（通常在最后一个 chunk）
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
        except Exception as e:
            # 捕获流处理中的所有异常，防止上层崩溃
            print(f"Stream error: {type(e).__name__}: {e}")
            traceback.print_exc()
        reasoning_text = "".join(collected_reasoning)
        full_text = "".join(collected_content)
        # 如果 finish_reason 是 tool_calls，则返回工具调用列表
        if finish_reason == "tool_calls":
            tool_calls_info = [tool_calls_dict[i] for i in sorted(tool_calls_dict.keys())]
            return full_text, tool_calls_info,reasoning_text
        else:
            return full_text, None,reasoning_text


    async def clear_messages(self) -> None:
        pass


    async def save_messages(self) -> None:
        pass

    def parse_tool_call_name(self,full_name: str):
        """
        将形如 "s{index}_{tool_name}" 的字符串解析为 (index, tool_name)
        例如: "s2_my_tool" -> (2, "my_tool")
        """
        match = re.match(r"^s(\d+)_(.+)$", full_name)
        if not match:
            raise ValueError(f"Invalid tool call name: {full_name}")
        index = int(match.group(1))
        original_name = match.group(2)
        return index, original_name

    def detect_image_mime_type(self,base64_string: str) -> str:
        """根据 Base64 数据的前几个字节识别图片 MIME 类型"""
        # 截取前 32 个字符解码（一般足够识别头信息）
        try:
            # 补充 padding 以防万一
            sample = base64_string[:32]
            # 确保长度是4的倍数，不足补 '='
            sample += '=' * (-len(sample) % 4)
            data = base64.b64decode(sample)
        except Exception:
            return "image/png"  

        # JPEG: FF D8 FF
        if data.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        # PNG: 89 50 4E 47
        if data.startswith(b'\x89PNG'):
            return "image/png"
        # WebP: RIFF .... WEBP
        if data.startswith(b'RIFF') and len(data) >= 12 and data[8:12] == b'WEBP':
            return "image/webp"
        # GIF: 47 49 46 38
        if data.startswith(b'GIF87') or data.startswith(b'GIF89'):
            return "image/gif"
        # BMP: 42 4D
        if data.startswith(b'BM'):
            return "image/bmp"
        
        return "image/png"




    
    async def process_query(self, query: str, base64_image: str|None=None,image_mime_type: str|None=None) -> str:
        """Process a query using Openai and available tools"""
        self.layer+=1
        print(f'\n当前层数：{self.layer}')
        dir_path = Path("chat_histories")
        if self.messagesId is not None:
            file_name = f"{self.messagesId}.json"
            file_path = dir_path / file_name
            with open(file_path, "r", encoding="utf-8") as f:
                messages = json.load(f)
        else:
            #写入系统提示符
            with open("C:/mcp_server/sysprompt/ServiceCode.md", 'r', encoding='utf-8') as file:
                        sysPrompt=file.read()
            messages:List[Dict[str, Any]]=[{
            "role":"system",
            "content": sysPrompt
            }]
            self.messagesId=uuid.uuid4()

        print(f'\nmessageid:{self.messagesId}')
        print(f'用户请求：{query}')
        if base64_image is None:
            messages.append(
                {
                    "role": "user",
                    "content": query
                }
            )
        else:
            mime_type = self.detect_image_mime_type(base64_image)
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url":f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            })
        while True:
            create_params = {
                "model": self.model,
                "messages": messages,
                "tools": self.available_tools,
                "tool_choice": "auto",
                "stream": True,
                "reasoning_effort": "low",
            }
            # 仅当模型为 deepseek-v4-flash-vision-exp 时添加额外参数
            if self.model == "deepseek-flash":
                create_params["extra_body"] = {"thinking": {"type": "enabled"}}
            stream = await self.llm_client.chat.completions.create(
                **create_params
            )
            reply_chunk, tool_calls_info, reasoning_text = await self._stream_response(stream)
            print("*助手回复结束")
            print()  # 换行，让提示符另起一行
            # Process response and handle tool calls
            if not tool_calls_info:
                # 将最终回复加入历史（跳出循环后再统一添加）
                break
            messages.append({
                "role": "assistant",
                "content": reply_chunk or None,  # 标准格式下通常为 None
                "tool_calls": tool_calls_info,
            })
            if self.preserve_thinking:
                messages[-1]["reasoning_content"] = reasoning_text

            #执行工具并收集结果。
            tool_results = []
            for tool_call in tool_calls_info:
                mcp_index,tool_name = self.parse_tool_call_name(tool_call["function"]["name"])
                tool_args = json.loads(tool_call["function"]["arguments"])
                print(f"调用工具：{tool_name},参数：{tool_args}")
                # Execute tool call
                result = await self.sessions[mcp_index].call_tool(tool_name, tool_args)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "content": "\n".join(
                        block.text
                        for block in result.content
                    ),
                })
                print(tool_results)
            messages.extend(tool_results)
        messages.append({
            "role": "assistant",
            "content": reply_chunk,
        })
        if self.preserve_thinking:
            messages[-1]["reasoning_content"] = reasoning_text
        file_name = f"{self.messagesId}.json"
        file_path = dir_path / file_name
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        self.layer-=1
        return str(self.messagesId)
    




    async def chat_loop(self) -> None:
        """Run an interactive chat loop"""
        while True:
            try:
                query = (await asyncio.to_thread(input, "\nQuery: ")).strip()
            except EOFError:
                break

            if query.lower() == 'quit':
                break
            try:
                await self.process_query(query)
            except Exception as e:
                print(f"\nError: {e}")


    async def rpc_server(self, host='127.0.0.1', port=9999):
        server = await asyncio.start_server(
            self.handle_rpc_client, host, port
        )
        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            server.close()
            await server.wait_closed()
                
    async def handle_rpc_client(self, reader, writer):
        try:
            reader._limit = 10 * 1024 * 1024
            data = await reader.readline()           
            if not data: return
            request = json.loads(data.decode().strip())
            method_name = request.get('method')
            args = request.get('args', [])
            # 安全限制：只允许特定方法（避免任意代码执行）
            if not hasattr(self, method_name):
                response = {'error': f'Method {method_name} not found'}
            else:
                method = getattr(self, method_name)
                if not callable(method):
                    response = {'error': f'{method_name} is not callable'}
                else:
                    # 调用实例方法，注意方法可能是协程或普通函数
                    if inspect.iscoroutinefunction(method):
                        result = await method(*args)
                    else:
                        result = method(*args)
                    response = {'result': result}
            writer.write((json.dumps(response) + '\n').encode())
            await writer.drain()
        except Exception as e:
            # 出错时返回错误
            writer.write((json.dumps({'error': str(e)}) + '\n').encode())
            await writer.drain()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except ConnectionResetError:
                        # 连接已被对端关闭，忽略此异常（Windows 常见）
                        pass

    #属性接口
    async def geTConversationLoopRunningLayer(self)->int:
        return self.layer

    async def getMassagesId(self)->str:
        return str(self.messagesId)

    async def clearMassagesId(self)->None:
        self.messagesId=None

    async def preserveChat(self):
        if self.preserve_messagesId is not None:
            raise RuntimeError("已有会话被锁定")
        self.preserve_messagesId=self.messagesId

    async def reloadChat(self):
        if self.preserve_messagesId is None:
            raise RuntimeError("无会话被锁定")
        self.messagesId=self.preserve_messagesId
        self.preserve_messagesId=None



    async def initSessions(self,stack:AsyncExitStack)->None:
        with open(self.server_config_path, "r", encoding="utf-8") as f:
            servers = json.load(f)
        for name, server in servers["mcpServers"].items():
            if server['type']=='stdio':
                if not os.path.exists(server['args'][0]):
                    print(f"{name}服务不存在")
                    continue
                if not os.path.exists(server['command']):
                    print(f"{name}命令不存在")
                    continue
                try:
                    read, write = await stack.enter_async_context(stdio_client(StdioServerParameters(command=server['command'], args=server['args'])))
                    session = await stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                except Exception as e:
                    print(f"服务 [{name}] 初始化失败: {type(e).__name__}: {e}")
                    continue
                tool_list = await session.list_tools()
                self.sessions.append(session)
                index = len(self.sessions) - 1   
                for tool in tool_list.tools:
                    self.available_tools.append({
                        "type": "function",
                        "function": {
                            "name": f"s{index}_{tool.name}",
                            "description": tool.description,
                            "parameters": tool.input_schema
                        }
                    })
            else:
                pass #未定义行为,等待扩展
            


    async def start(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            await self.initSessions(stack)
            rpc_task = asyncio.create_task(self.rpc_server(host='127.0.0.1', port=9999))
            await self.chat_loop()
            rpc_task.cancel()
            try:
                await rpc_task
            except asyncio.CancelledError:
                pass




if __name__ == "__main__":
    mcpClient = MCPClient(
        base_url=os.environ.get("MCP_BASE_URL"),
        api_key=os.environ.get("MCP_API_KEY"),
        config_path=r"C:\mcp_server\config\serverPaths.json",
        model=os.environ.get("MCP_MODEL")
    )
    try:
        asyncio.run(mcpClient.start())
    except KeyboardInterrupt:
        # 用户主动 Ctrl+C，静默退出
        pass
    except asyncio.CancelledError:
        pass
    finally:
        print("\n已退出")
        # 强制退出，避免残留的非守护线程（input 线程）拖住解释器
        os._exit(0)