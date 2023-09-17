import yaml
from pydantic import BaseModel
from typing import List, Dict


class Param(BaseModel):
    name: str
    type: str
    description: str


class Skill(BaseModel):
    name: str
    description: str
    params: List[Param]
    return_: List[Param]


class Character(BaseModel):
    name: str
    description: str
    goal: str
    basic_skills: List[str]
    special_skills: List[str]


class GameMasterInstruction(BaseModel):
    instructions: List[str]
    skills: List[str]


class PlayerCombination(BaseModel):
    size: str
    number: int
    players: List[str]


class Game(BaseModel):
    name: str
    description: str
    rules: List[str]
    game_master: GameMasterInstruction
    characters: List[Character]
    victory_conditions: List[str]
    player_combination: List[PlayerCombination]
    utils: List[Skill]

    def get_player_number(self) -> List[int]:
        return [len(x) for x in self.player_combination]


if __name__ == "__main__":
    with open(
        "/Users/zhangyuchen/projects/table_game/src/prompts/werewolves.yaml",
        "r",
        encoding="utf-8",
    ) as file:
        game_data = yaml.safe_load(file)["game"]

    game = Game(**game_data)

    # 访问数据
    print(game)  # 输出: 狼人杀
