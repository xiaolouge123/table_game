import enum
import asyncio
from typing import List
from abc import ABC, abstractmethod
from loguru import logger

from agents.agent import Role, Liveliness, DummyAgent, GMAgent
from prompts.history import Action
from prompts.game_content import Game


class BoardState(enum.Enum):
    INIT = 0
    RUNNING = 1
    DONE = 2


class WereWolvesStatus(enum.Enum):
    DAY = 0
    NIGHT = 1
    VOTING = 2


class Board(ABC):
    @abstractmethod
    def parley(self):
        pass

    # @abstractmethod
    # def exit(self):
    #     pass

    # @abstractmethod
    # def dump(self):
    #     pass

    @abstractmethod
    def register_agents(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @property
    @abstractmethod
    def state(self):
        pass

    @state.setter
    @abstractmethod
    def state(self, state):
        pass


class WereWolvesBoard(Board):
    def __init__(self, manager, id) -> None:
        self._state = BoardState.INIT
        self._register_agents = []  # all agents for this game
        self.gm_agent = None  # game master agent for this game
        self.other_agents = []  # non-gm and non-human agents for this game
        self.ws_manager = manager
        self.id = id
        self.game = None

    @classmethod
    def create_agents(cls, websocket_agent: List[any]):
        return [GMAgent()]

    def register_agents(self, human_agents, other_agents):
        for agent in human_agents:
            self._register_agents.append(agent)
        for agent in other_agents:
            if agent.role == Role.GM.name:
                self.gm_agent = agent
            else:
                self.other_agents.append(agent)
                self._register_agents.append(agent)

    def load_disk(self, game: Game):
        self.game = game

    async def parley(self):
        logger.info(f"GM {self.gm_agent}")
        act = await self.gm_agent.act()
        await self.broadcast2all(act)
        logger.info(self._register_agents)
        for idx, agent in enumerate(self._register_agents):
            logger.info(f"Agent {agent.id} is {agent.liveliness}")
            if agent.liveliness == Liveliness.ALIVE.name:
                act = await agent.act()
                nxt_spk_id = self.find_next_speaker_id(idx, self._register_agents)
                await self.broadcast2all(act, next_speaker_id=nxt_spk_id)
            else:
                continue
        logger.info("Parley done")

    def find_next_speaker_id(self, idx, candidate_agents):
        while idx + 1 < len(candidate_agents):
            if candidate_agents[idx + 1].liveliness == Liveliness.ALIVE.name:
                return candidate_agents[idx + 1].id
            idx += 1
        return None

    async def broadcast2all(self, act: Action, **kwargs):
        await self.ws_manager.broadcast(
            act.text, sender=act.sender_id, room_id=self.id, **kwargs
        )  # external human agent
        for agent in self.other_agents:
            await agent.observe(act, **kwargs)  # internal agent

    async def start(self):
        #
        while True:
            logger.info("A new round")
            await self.parley()
            await asyncio.sleep(1)

    async def initializiing(self):
        """
        initial all game related informations and dispacth these to each players(human, agent and gm etc.)
        1. character assignment for each player
        2. send inital state message to each player
        """
        pass

    def assigne_character(self):
        pass

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        assert isinstance(state, BoardState)
        self._state = state
