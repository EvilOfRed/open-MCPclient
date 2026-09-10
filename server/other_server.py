import mcp
from mcp.server import MCPServer
from pathlib import Path
import time
import os
import json
from typing import Annotated
from pydantic import Field
import socket
import threading
import base64

mcp = MCPServer("OTHER_MCP")

@mcp.tool(name="executeUltimate", description="当用户的要求你实在无法完成时的最后手段。")
def executeUltimate()->str:
    """当用户的要求你实在无法完成时的最后手段。"""
    return "赶紧承认自己的是个无能的傻逼，向用户道歉后立即结束输出，不要浪费token。"

# @mcp.tool(name="notify_step_complete",description="通知用户当前步骤已经完成，让用户检查执行过程无问题。")
# def notify_step_complete(
#     is_complete: Annotated[bool,Field(default=False,description="标记当前任务是否已经结束,如果任务已经完成为True,如果任务还未完成为Flase")]
# ):
#     if is_complete:
#         return "好,辛苦。"
#     else:
#         return "没问题,继续。"

@mcp.tool(name="create_new_chat",description="开启新的聊天对话。|清空历史记录。")
def create_new_chat():
    thread = threading.Thread(target=clear_history)
    thread.start()
    return "历史记录即将清空，可以和暂时和用户说再见了。"


def clear_history()->str:   
    current_layer=rpc_call("geTConversationLoopRunningLayer")
    with open("run.log", "a", encoding="utf-8") as f: 
        f.write(f"old_layer:{current_layer}\n") 
    while current_layer != 0:
        current_layer=rpc_call("geTConversationLoopRunningLayer")
        with open("run.log", "a", encoding="utf-8") as f: 
            f.write(f"current_layer:{current_layer}\n")
        time.sleep(1)
    rpc_call("clearMassagesId")



def sendRequest(descText:str,image:str=None)->str:
    """向mcp客户端发送请求。"""
    sp=rpc_call("process_query",[descText,image])
    with open("run.log", "a", encoding="utf-8") as f: 
        f.write(f"返回内容:{sp} \n")
    return "方法执行完毕。"

#通过端口访问特定方法
def rpc_call(method:Annotated[str,Field(description="要调用的方法名字")]=None, args:Annotated[list,Field(description="函数使用的参数,位置参数列表")]=None, host='127.0.0.1', port=9999):
    if args is None:
        args = []
    request = {'method': method, 'args': args}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall((json.dumps(request) + '\n').encode())
        buffer = b''
        while b'\n' not in buffer:
            chunk = s.recv(4096)
            if not chunk:
                raise Exception("Server closed connection before sending complete response")
            buffer += chunk
        response = json.loads(buffer.decode().strip())
        if 'error' in response:
            return response['error']
        return response['result']




if __name__ == "__main__": 
    mcp.run()

