from typing import Literal

from pydantic import BaseModel, Field


class Token(BaseModel):
    kind: str = ''
    text: str = ''

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


class Text(Token):
    kind: Literal['text'] = 'text'


class Highlight(Token):
    kind: Literal['highlight'] = 'highlight'
    tone: Literal['desc', 'card'] = 'desc'


class Buff(Token):
    kind: Literal['buff'] = 'buff'
    icon: str = ''
    bg: str = ''
    effect_name: str = Field('', alias='effectName')
    stamina: bool = False


class Break(Token):
    kind: Literal['break'] = 'break'


def serialize(tokens: list[Token]) -> list[dict]:
    return [t.to_dict() for t in tokens]
