from dataclasses import dataclass

from .sqlite import select, select_many
from .constants import ExamEffectType, ShowExamEffectType


@dataclass
class IdolCard:
    """偶像卡"""
    id: str
    skin_id: str
    exam_effect_type: ExamEffectType
    show_exam_effect_type: ShowExamEffectType
    is_another: bool
    another_name: str | None
    name: str

    @classmethod
    def from_skin_id(cls, sid: str) -> 'IdolCard | None':
        """
        根据 skin_id 查询 IdolCard。
        """
        row = select("""
        SELECT
            IC.id AS cardId,
            ICS.id AS skinId,
            IC.examEffectType AS examEffectType,
            IC.showExamEffectType AS showExamEffectType,
            Char.lastName || ' ' || Char.firstName || '　' || IC.name AS name,
            NOT (IC.originalIdolCardSkinId = ICS.id) AS isAnotherVer,
            ICS.name AS anotherVerName
        FROM IdolCard IC
        JOIN Character Char ON characterId = Char.id
        JOIN IdolCardSkin ICS ON IC.id = ICS.idolCardId
        WHERE ICS.id = ?;
        """, sid)
        if row is None:
            return None
        return cls(
            id=row["cardId"],
            skin_id=row["skinId"],
            exam_effect_type=ExamEffectType(row["examEffectType"]),
            show_exam_effect_type=ShowExamEffectType(row["showExamEffectType"]),
            is_another=bool(row["isAnotherVer"]),
            another_name=row["anotherVerName"],
            name=row["name"]
        )

    @classmethod
    def all(cls) -> list['IdolCard']:
        """获取所有偶像卡"""
        rows = select_many("""
        SELECT
            IC.id AS cardId,
            ICS.id AS skinId,
            IC.examEffectType AS examEffectType,
            IC.showExamEffectType AS showExamEffectType,
            Char.lastName || ' ' || Char.firstName || '　' || IC.name AS name,
            NOT (IC.originalIdolCardSkinId = ICS.id) AS isAnotherVer,
            ICS.name AS anotherVerName
        FROM IdolCard IC
        JOIN Character Char ON characterId = Char.id
        JOIN IdolCardSkin ICS ON IC.id = ICS.idolCardId;
        """)
        results = []
        for row in rows:
            results.append(cls(
                id=row["cardId"],
                skin_id=row["skinId"],
                exam_effect_type=ExamEffectType(row["examEffectType"]),
                show_exam_effect_type=ShowExamEffectType(row["showExamEffectType"]),
                is_another=bool(row["isAnotherVer"]),
                another_name=row["anotherVerName"],
                name=row["name"]
            ))
        return results


if __name__ == '__main__':
    from pprint import pprint as print

    print(IdolCard.from_skin_id('i_card-skin-fktn-3-006'))
    print(IdolCard.all())
