import os
import json
import uuid
import re
import logging
from typing import Literal
from pydantic import BaseModel, ConfigDict, ValidationError

from kaa.errors import ProduceSolutionInvalidError, ProduceSolutionNotFoundError

from .const import ProduceAction, HajimeScenario, HifScenario, ProduceStrategy, Scenario
from .validation import ConfigIssue

logger = logging.getLogger(__name__)

class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class ProduceData(ConfigBaseModel):
    mode: Scenario = HajimeScenario.REGULAR
    """
    培育模式（剧本 + 难度，如 hajime_regular / nia_pro / hif_qualify）。
    """
    produce_strategy: ProduceStrategy = ProduceStrategy.NORMAL
    """
    培育策略。

    不同剧本支持的策略不同：初/NIA 仅支持「普通」，HIF 仅支持「正赛弃赛」。
    """
    idol: str | None = None
    """
    要培育偶像的 IdolCardSkin.id。

    仅适用于 初/NIA 剧本；HIF 剧本下该字段无效（UI 隐藏且流程不使用）。
    """
    memory_set: int | None = None
    """要使用的回忆编成编号，从 1 开始。"""
    support_card_set: int | None = None
    """要使用的支援卡编成编号，从 1 开始。"""
    auto_set_memory: bool = False
    """是否自动编成回忆。此选项优先级高于回忆编成编号。"""
    auto_set_support_card: bool = False
    """是否自动编成支援卡。此选项优先级高于支援卡编成编号。"""
    use_pt_boost: bool = False
    """是否使用支援强化 Pt 提升。"""
    use_note_boost: bool = False
    """是否使用笔记数提升。"""
    follow_producer: bool = False
    """是否关注租借了支援卡的制作人。"""
    self_study_lesson: Literal['dance', 'visual', 'vocal'] = 'dance'
    """自习课类型。"""
    prefer_lesson_ap: bool = False
    """
    优先 SP 课程。

    启用后，若出现 SP 课程，则会优先执行 SP 课程，而不是推荐课程。
    若出现多个 SP 课程，随机选择一个。
    """
    battle_strategy: Literal['bandai', 'expert'] = 'bandai'
    """战斗策略。"""
    actions_order: list[ProduceAction] = [
        ProduceAction.RECOMMENDED,
        ProduceAction.VISUAL,
        ProduceAction.VOCAL,
        ProduceAction.DANCE,
        ProduceAction.ALLOWANCE,
        ProduceAction.OUTING,
        ProduceAction.STUDY,
        ProduceAction.CONSULT,
        ProduceAction.REST,
    ]
    """
    行动优先级

    每一周的行动将会按这里设置的优先级执行。
    """
    use_ap_drink: bool = False
    """
    AP 不足时自动使用 AP 饮料
    """
    skip_commu: bool = True
    """检测并跳过交流"""
    card_deck_id: str | None = None
    """
    卡组配置 ID。

    为 None 时使用默认卡组（deck_defaults.py 中的系统预设）。
    自定义卡组请放到 conf/decks/ 目录下。
    """

class ProduceSolution(ConfigBaseModel):
    """培育方案"""
    type: Literal['produce_solution'] = 'produce_solution'
    """方案类型标识"""
    id: str
    """方案唯一标识符"""
    name: str
    """方案名称"""
    description: str | None = None
    """方案描述"""
    data: ProduceData
    """培育数据"""


def validate_produce_solution(solution: ProduceSolution) -> list[ConfigIssue]:
    """校验培育方案的业务规则（纯逻辑，不访问游戏数据）。

    用于两个场景：
    1. UI 保存时调用，阻止写入无效配置；
    2. 培育任务启动时调用，以友好提示替代运行时崩溃（如 step3 的 assert）。

    :param solution: 待校验的培育方案。
    :return: 校验问题列表，为空表示无问题。
    """
    data = solution.data
    issues: list[ConfigIssue] = []
    is_hif = isinstance(data.mode, HifScenario)

    # 培育策略必须匹配剧本：初/NIA 仅支持「普通」，HIF 仅支持「正赛弃赛」
    if is_hif:
        if data.produce_strategy != ProduceStrategy.WITHDRAW_MAIN:
            issues.append(ConfigIssue(
                severity='error',
                field='produce_strategy',
                message='HIF 剧本仅支持培育策略「正赛弃赛」。',
            ))
    elif data.produce_strategy != ProduceStrategy.NORMAL:
        issues.append(ConfigIssue(
            severity='error',
            field='produce_strategy',
            message='初 / NIA 剧本仅支持培育策略「普通」。',
        ))

    # 回忆/支援卡编成与偶像选择仅在非 HIF 剧本下要求；
    # HIF 使用游戏内自动选中的回忆，这些字段不参与流程。
    if not is_hif:
        # 回忆编成必须配置「编号」或「自动编成」至少其一，否则 STEP3 无法继续
        if data.memory_set is None and not data.auto_set_memory:
            issues.append(ConfigIssue(
                severity='error',
                field='memory_set',
                message='回忆编成未配置：请填写「回忆编成编号」，或勾选「自动编成回忆」。',
            ))

        # 支援卡编成必须配置「编号」或「自动编成」至少其一，否则 STEP2 无法继续
        if data.support_card_set is None and not data.auto_set_support_card:
            issues.append(ConfigIssue(
                severity='error',
                field='support_card_set',
                message='支援卡编成未配置：请填写「支援卡编成编号」，或勾选「自动编成支援卡」。',
            ))

        # 偶像必选
        if not data.idol:
            issues.append(ConfigIssue(
                severity='error',
                field='idol',
                message='未选择要培育的偶像。',
            ))

    # 行动优先级列表不能为空，否则培育时找不到可执行行动
    if not data.actions_order:
        issues.append(ConfigIssue(
            severity='error',
            field='actions_order',
            message='行动优先级列表不能为空。',
        ))

    return issues


class ProduceSolutionManager:
    """培育方案管理器（单例）"""

    _instance: 'ProduceSolutionManager | None' = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cached_list = None
        return cls._instance

    def __init__(self) -> None:
        """初始化管理器，确保方案目录存在。"""
        os.makedirs(self.SOLUTIONS_DIR, exist_ok=True)

    SOLUTIONS_DIR = "conf/produce"

    def _sanitize_filename(self, name: str) -> str:
        """
        清理文件名中的非法字符

        :param name: 原始名称
        :return: 清理后的文件名
        """
        # 替换 \/:*?"<>| 为下划线
        return re.sub(r'[\\/:*?"<>|]', '_', name)

    def _get_file_path(self, name: str) -> str:
        """
        根据方案名称获取文件路径

        :param name: 方案名称
        :return: 文件路径
        """
        safe_name = self._sanitize_filename(name)
        return os.path.join(self.SOLUTIONS_DIR, f"{safe_name}.json")

    def _find_file_path_by_id(self, id: str) -> str | None:
        """
        根据方案ID查找文件路径

        :param id: 方案ID
        :return: 文件路径，如果未找到则返回 None
        """
        if not os.path.exists(self.SOLUTIONS_DIR):
            return None

        for filename in os.listdir(self.SOLUTIONS_DIR):
            if filename.endswith('.json'):
                try:
                    file_path = os.path.join(self.SOLUTIONS_DIR, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('id') == id:
                        return file_path
                except Exception:
                    continue
        return None

    def new(self, name: str) -> ProduceSolution:
        """
        创建新的培育方案

        :param name: 方案名称
        :return: 新创建的方案
        """
        solution = ProduceSolution(
            id=uuid.uuid4().hex,
            name=name,
            data=ProduceData()
        )
        return solution

    def list(self) -> list[ProduceSolution]:
        """
        列出所有培育方案

        :return: 方案列表
        """
        if self._cached_list is not None:
            return self._cached_list

        solutions = []
        if not os.path.exists(self.SOLUTIONS_DIR):
            return solutions

        for filename in os.listdir(self.SOLUTIONS_DIR):
            if filename.endswith('.json'):
                try:
                    file_path = os.path.join(self.SOLUTIONS_DIR, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        solution = ProduceSolution.model_validate_json(f.read())
                    solutions.append(solution)
                    logger.info(f"Loaded produce solution from {file_path}")
                except Exception:
                    logger.warning(f"Failed to load produce solution from {file_path}")
                    continue

        self._cached_list = solutions
        return solutions

    def delete(self, id: str) -> None:
        """
        删除指定ID的培育方案

        :param id: 方案ID
        """
        file_path = self._find_file_path_by_id(id)
        if file_path:
            os.remove(file_path)
            self._cached_list = None

    def save(self, id: str, solution: ProduceSolution) -> None:
        """
        保存培育方案

        :param id: 方案ID
        :param solution: 方案对象
        """
        os.makedirs(self.SOLUTIONS_DIR, exist_ok=True)

        # 确保ID一致
        solution.id = id

        # 先删除具有相同ID的旧文件（如果存在），避免名称变更时产生重复文件
        old_file_path = self._find_file_path_by_id(id)
        if old_file_path:
            os.remove(old_file_path)

        # 保存新文件
        file_path = self._get_file_path(solution.name)
        with open(file_path, 'w', encoding='utf-8') as f:
            # 使用 model_dump 并指定 mode='json' 来正确序列化枚举
            data = solution.model_dump(mode='json')
            json.dump(data, f, ensure_ascii=False, indent=4)

        self._cached_list = None

    def read(self, id: str) -> ProduceSolution:
        """
        读取指定ID的培育方案

        :param id: 方案ID
        :return: 方案对象
        :raises ProduceSloutionNotFoundError: 当方案不存在时
        """
        file_path = self._find_file_path_by_id(id)
        if not file_path:
            raise ProduceSolutionNotFoundError(id)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return ProduceSolution.model_validate_json(f.read())
        except ValidationError as e:
            raise ProduceSolutionInvalidError(id, file_path, e)

    def duplicate(self, id: str) -> ProduceSolution:
        """
        复制指定ID的培育方案

        :param id: 要复制的方案ID
        :return: 新的方案对象（具有新的ID和名称）
        :raises ProduceSolutionNotFoundError: 当原方案不存在时
        """
        original = self.read(id)

        # 生成新的ID和名称
        new_id = uuid.uuid4().hex
        new_name = f"{original.name} - 副本"

        # 创建新的方案对象
        new_solution = ProduceSolution(
            type=original.type,
            id=new_id,
            name=new_name,
            description=original.description,
            data=original.data.model_copy()  # 深拷贝数据
        )

        return new_solution

    def name_exists(self, name: str, exclude_id: str | None = None) -> bool:
        """检查指定名称是否已被其他方案使用。

        :param name: 要检查的名称。
        :param exclude_id: 排除的方案 ID（用于重命名时排除自身）。
        :return: 名称已存在返回 True。
        """
        solutions = self.list()
        for sol in solutions:
            if sol.name == name:
                if exclude_id is None or sol.id != exclude_id:
                    return True
        return False