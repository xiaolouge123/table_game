import enum
import uuid
from typing import List
from prompts.history import Message, Action
from abc import ABC, abstractmethod


class Role(enum.Enum):
    HUMAN = 0
    AGENT = 1
    GM = 2


class Liveliness(enum.Enum):
    ALIVE = 0
    DEAD = 1


class Agent(ABC):
    @abstractmethod
    async def observe(self, observation):
        pass

    @abstractmethod
    async def act(self):
        pass

    @property
    @abstractmethod
    def liveliness(self):
        pass

    @liveliness.setter
    @abstractmethod
    def liveliness(self, liveliness):
        pass


class GMAgent(Agent):
    """
    let gm follow the rules, it has to automatically arrange the game
    """

    def __init__(self) -> None:
        self._role = Role.GM
        self._liveliness = Liveliness.ALIVE
        self._history: List[Message] = []
        self.agent_id = str(uuid.uuid4())[:4]

    async def observe(self, act: Action):
        pass

    async def act(self) -> Action:
        return Action("Close your eyes in the night", self.role)

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
    def liveliness(self):
        return self._liveliness.name

    @property
    def history(self):
        return self._history

    @property
    def character(self):
        return self._character

    @character.setter
    def character(self, character: str):
        self._character = character


class DummyAgent(Agent):
    def __init__(self) -> None:
        self._role = Role.AGENT
        self._liveliness = Liveliness.ALIVE
        self.agent_id = str(uuid.uuid4())[:4]

    async def observe(self, observation):
        return

    async def act(self):
        return Action("la bu la bu la bu", self.get_role())

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
    def liveliness(self):
        return self._liveliness.name

    @liveliness.setter
    def liveliness(self, liveliness: Liveliness):
        self._liveliness = liveliness

    @property
    def character(self):
        return self._character

    @character.setter
    def character(self, character: str):
        self._character = character


class OpenaiApiAgent(Agent):
    """
    let the agent balance its benefit, it has to make the biggest outcome
    """

    def __init__(self) -> None:
        self._role = Role.AGENT
        self.api_host = ""
        self.agent_id = str(uuid.uuid4())[:4]

    async def observe(self, observation):
        return

    async def act(self):
        return {"text": "la bu la bu la bu"}

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
    def liveliness(self):
        return self._liveliness.name

    @liveliness.setter
    def liveliness(self, liveliness: Liveliness):
        self._liveliness = liveliness

    @property
    def character(self):
        return self._character

    @character.setter
    def character(self, character: str):
        self._character = character
