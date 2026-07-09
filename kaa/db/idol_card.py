from dataclasses import dataclass
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field

from kaa.db._util import register_cache_clear, row_dict
from kaa.db.sqlite import select, select_many

_IDOL_CARD_SELECT = """
SELECT
    IC.id AS cardId,
    ICS.id AS skinId,
    Char.lastName || ' ' || Char.firstName || '　' || IC.name AS name,
    NOT (IC.originalIdolCardSkinId = ICS.id) AS isAnotherVer,
    ICS.name AS anotherVerName,
    Char.id AS characterId,
    Char.lastName || ' ' || Char.firstName AS characterName
FROM IdolCard IC
JOIN Character Char ON characterId = Char.id
JOIN IdolCardSkin ICS ON IC.id = ICS.idolCardId
""".strip()


class IdolCardRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(alias='cardId')
    skin_id: str = Field(alias='skinId')
    name: str
    is_another: bool = Field(alias='isAnotherVer')
    another_name: str | None = Field(None, alias='anotherVerName')
    character_id: str = Field(alias='characterId')
    character_name: str = Field(alias='characterName')


@dataclass
class IdolCard:
    """偶像卡"""
    id: str
    skin_id: str
    is_another: bool
    another_name: str | None
    name: str
    character_id: str
    character_name: str

    @classmethod
    def from_skin_id(cls, sid: str) -> 'IdolCard | None':
        """根据 skin_id 查询 IdolCard。"""
        row = select(f'{_IDOL_CARD_SELECT} WHERE ICS.id = ?;', sid)
        if row is None:
            return None
        return cls._from_row(row)

    @classmethod
    def all(cls) -> list['IdolCard']:
        """获取所有偶像卡"""
        return list(_all_cached())

    @classmethod
    def _from_row(cls, row) -> 'IdolCard':
        parsed = IdolCardRow.model_validate(row_dict(row))
        return cls(
            parsed.card_id,
            parsed.skin_id,
            parsed.is_another,
            parsed.another_name,
            parsed.name,
            parsed.character_id,
            parsed.character_name,
        )


@lru_cache(maxsize=1)
def _all_cached() -> tuple[IdolCard, ...]:
    rows = select_many(f'{_IDOL_CARD_SELECT};')
    return tuple(IdolCard._from_row(row) for row in rows)


register_cache_clear(_all_cached.cache_clear)