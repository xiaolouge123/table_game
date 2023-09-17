import typing
import uuid
import asyncio
from loguru import logger
from asyncio import Queue, QueueEmpty
from starlette.websockets import WebSocket as StarletteWebSocket
from agents.agent import Agent, Role, Liveliness
from prompts.history import Action


class WebSocketAgent(StarletteWebSocket, Agent):
    def __init__(self, websocket):
        super().__init__(
            scope=websocket.scope, receive=websocket._receive, send=websocket._send
        )
        self.ws_id = str(uuid.uuid4())[:4]
        self.agent_id = self.ws_id
        self._role = Role.HUMAN
        self._liveliness = Liveliness.ALIVE
        self._character = None
        self._msg_queue = Queue()
        self.bg_task = asyncio.create_task(self.read_from_ws_conn())

    async def send_masseage(self, text: str = "", **kwargs) -> None:
        """
        send json message, the struct is like
            "message_type": "meta"|"msg"
            "text": "" str
            "agent_id": websocket.id, # 声明信息接受者
            "role": websocket.role,
            "liveliness": websocket.liveliness,
            "character": websocket.character,
            "next_speaker_id": websocket.agent_id,
        """
        data = {
            "text": text,
            "message_type": kwargs.get("message_type", "msg"),
            "agent_id": self.id,  # yourself id
            "role": self.role,  # yourself role
            "liveliness": self.liveliness,
            "character": self.character,
        }
        nxt_spk_id = kwargs.get("next_speaker_id", None)  # 声明下一个发言人
        if nxt_spk_id:
            data.update(next_speaker_id=nxt_spk_id)
        sender_id = kwargs.get("sender_id", None)  # 声明信息发送人
        if sender_id:
            data.update(sender_id=sender_id)

        await self.send_json(data)

    async def observe(self, act: Action, **kwargs):
        """
        send message to the websocket user/send msg to human
        """
        logger.info(f"Agent {self.id} observe {act.text}")
        await self.send_masseage(text=act.text, sender_id=act.sender_id, **kwargs)

    async def act(self):
        logger.info("Waiting for human action")
        while True:
            """
            try to get message from the queue, if not, wait for 0.1s
            """
            try:
                msg = self._msg_queue.get_nowait()
                break
            except QueueEmpty:
                await asyncio.sleep(0.1)
                continue
        return Action(msg, sender_id=self.role)

    async def read_from_ws_conn(self):
        try:
            while True:
                logger.info("Waiting for on message")
                msg = await self.receive_text()
                await self.put_data(msg)

        except asyncio.CancelledError:
            pass

    async def put_data(self, message: str):
        try:
            await self._msg_queue.put(message)
        except asyncio.CancelledError:
            pass

    async def on_first_message(self):
        data = {"message_type": "meta"}
        await self.send_masseage(**data)

    def get_role(self):
        return self.role

    @property
    def id(self):
        return self.agent_id

    @property
    def role(self):
        return self._role.name

    @role.setter
    def role(self, role: Role):
        self._role = role

    @property
    def character(self):
        return self._character

    @character.setter
    def character(self, character: str):
        self._character = character

    @property
    def liveliness(self):
        return self._liveliness.name

    @liveliness.setter
    def liveliness(self, liveliness: Liveliness):
        self._liveliness = liveliness
