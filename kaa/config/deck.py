import os
import json
import uuid
import re
import logging
from functools import cached_property
from typing import Literal, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, ValidationError

if TYPE_CHECKING:
    from kaa.db.skill_card import SkillCard

class CardDeckNotFoundError(FileNotFoundError):
    def __init__(self, id: str):
        super().__init__(f"Card deck not found: {id}")

class CardDeckInvalidError(ValueError):
    def __init__(self, id: str, file_path: str, cause: Exception):
        super().__init__(f"Invalid card deck file: {file_path} (id={id}): {cause}")

logger = logging.getLogger(__name__)


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class CardDeck(ConfigBaseModel):
    """卡组配置"""
    type: Literal['card_deck'] = 'card_deck'
    """配置类型标识"""
    id: str
    """卡组唯一标识符"""
    name: str
    """卡组名称"""
    description: str | None = None
    """卡组描述"""
    archetype: str
    """该卡组适用的考试流派（ProduceExamEffectType 枚举值）。"""
    cards: list[list[str]]
    """
    卡牌优先级分层列表。

    外层 index 越小优先级越高。
    内层 list 中的卡在同层内平等，按出现位置 tie-break。
    未出现在任何内层 list 中的卡默认最低优先级。
    """

    @cached_property
    def _priority_map(self) -> dict[str, int]:
        pm: dict[str, int] = {}
        for tier_idx, cards in enumerate(self.cards):
            for cid in cards:
                if cid not in pm:
                    pm[cid] = tier_idx
        return pm

    def query_priority(self, card_or_id: 'str | SkillCard') -> int:
        if isinstance(card_or_id, str):
            return self._priority_map.get(card_or_id, 999)
        return self._priority_map.get(card_or_id._id, 999)


class CardDeckManager:
    """卡组管理器"""

    _instance: 'CardDeckManager | None' = None

    DECKS_DIR = "conf/decks"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _sanitize_filename(self, name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', '_', name)

    def _get_file_path(self, name: str) -> str:
        safe_name = self._sanitize_filename(name)
        return os.path.join(self.DECKS_DIR, f"{safe_name}.json")

    def _find_file_path_by_id(self, id: str) -> str | None:
        if not os.path.exists(self.DECKS_DIR):
            return None
        for filename in os.listdir(self.DECKS_DIR):
            if filename.endswith('.json'):
                try:
                    file_path = os.path.join(self.DECKS_DIR, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('id') == id:
                        return file_path
                except Exception:
                    continue
        return None

    def list(self) -> list[CardDeck]:
        if not os.path.exists(self.DECKS_DIR):
            return []
        decks = []
        for filename in os.listdir(self.DECKS_DIR):
            if filename.endswith('.json'):
                try:
                    file_path = os.path.join(self.DECKS_DIR, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        deck = CardDeck.model_validate_json(f.read())
                    decks.append(deck)
                    logger.info(f"Loaded card deck from {file_path}")
                except Exception:
                    logger.warning(f"Failed to load card deck from {file_path}")
                    continue
        return decks

    def read(self, id: str) -> CardDeck:
        file_path = self._find_file_path_by_id(id)
        if not file_path:
            raise CardDeckNotFoundError(id)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return CardDeck.model_validate_json(f.read())
        except ValidationError as e:
            raise CardDeckInvalidError(id, file_path, e)

    def save(self, id: str, deck: CardDeck) -> None:
        os.makedirs(self.DECKS_DIR, exist_ok=True)
        deck.id = id
        old_file_path = self._find_file_path_by_id(id)
        if old_file_path:
            os.remove(old_file_path)
        file_path = self._get_file_path(deck.name)
        with open(file_path, 'w', encoding='utf-8') as f:
            data = deck.model_dump(mode='json')
            json.dump(data, f, ensure_ascii=False, indent=4)

    def delete(self, id: str) -> None:
        file_path = self._find_file_path_by_id(id)
        if file_path:
            os.remove(file_path)

    def new(self, name: str, archetype: str) -> CardDeck:
        return CardDeck(
            id=uuid.uuid4().hex,
            name=name,
            archetype=archetype,
            cards=[],
        )

    def name_exists(self, name: str, exclude_id: str | None = None) -> bool:
        decks = self.list()
        for d in decks:
            if d.name == name:
                if exclude_id is None or d.id != exclude_id:
                    return True
        return False
