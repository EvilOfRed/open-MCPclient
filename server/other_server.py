import mcp
from mcp.server import MCPServer
from pathlib import Path
import time
import os
import json
from typing import Annotated,List
from pydantic import Field
import threading
from rpc_utils import  sendRequest, clearHistory

mcp = MCPServer("OTHER_MCP")

base_url = "http://127.0.0.1:8721"

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
    thread = threading.Thread(target=clearHistory)
    thread.start()
    return "结束输出后，历史记录将清空。"





if __name__ == "__main__": 
    mcp.run()

