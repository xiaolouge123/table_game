from typing import Optional, Dict, List
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str
    additional_kwargs: Optional[Dict[str, str]]


class Turn(BaseModel):
    index: int = 0
    messages: List[Message] = []


class History(BaseModel):
    turns: List[Turn] = []


class Action:
    def __init__(self, text: str, sender_id: str):
        self.text = text
        self.sender_id = sender_id

    def to_dict(self):
        return {"text": self.text, "sender_id": self.sender_id}
