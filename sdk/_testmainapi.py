# Simple library-esque to handle websockets

import asyncio
import json
import time
import uuid
import sys
sys.path.append(".")
sys.path.append("../../../")

import websockets

URL = "ws://127.0.0.1/api/ws/"

class Bot():
    def __init__(self, bot_id: int, token: str, send_all: bool = True, send_none: bool = True):
        self.bot_id = bot_id
        self.token = token
        self.send_all = send_all
        self.send_none = send_none
        self.hooks = {"identity": self.identity, "default": self.default}
        self.websocket = None

    async def _render_event(self, event):
        for m in event.split("\x1f"):
            for e in m.split("\x1f"):
                if e == "":
                    continue
                e_json = json.loads(e)
                if e_json.get("m"):
                    e_type = e_json["m"].get("e")
                    func = self.hooks.get(e_type)
                    if func:
                        await func(e_json)
                        return
                elif e_json.get("control"):
                    try:
                        await self.hooks[e_json["code"]](e_json)
                    except Exception:
                        pass

                await self.hooks["default"](e_json)

    async def _ws_handler(self):
        async with websockets.connect(URL) as self.websocket:
            while True:
                event = await self.websocket.recv()
                print(f"GOT {event}")
                await self._render_event(event)
    
    async def identity(self, event):
        payload = {"id": str(self.bot_id), "token": self.token, "bot": True, "send_all": self.send_all, "send_none": self.send_none}
        await self.websocket.send(json.dumps(payload))
        print(f"Sending {json.dumps(payload)}")
    
    async def default(self, event):
        ...
        
    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_handler())

