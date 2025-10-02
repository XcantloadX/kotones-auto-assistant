import os
import json
import uuid
import re
import logging
from typing import Literal
from pydantic import BaseModel, ConfigDict, ValidationError, field_serializer, field_validator

from kaa.errors import ProduceSolutionInvalidError, ProduceSolutionNotFoundError

from .const import ProduceAction, RecommendCardDetectionMode

logger = logging.getLogger(__name__)

class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class ProduceData(ConfigBaseModel):
    mode: Literal['regular', 'pro', 'master'] = 'regular'
    """
    培育模式。
    进行一次 REGULAR 培育需要 ~30min，进行一次 PRO 培育需要 ~1h（具体视设备性能而定）。
    """
    idol: str | None = None
    """
    要培育偶像的 IdolCardSkin.id。
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
    recommend_card_detection_mode: RecommendCardDetectionMode = RecommendCardDetectionMode.NORMAL
    """
    推荐卡检测模式

    严格模式下，识别速度会降低，但识别准确率会提高。
    """
    use_ap_drink: bool = False
    """
    AP 不足时自动使用 AP 饮料
    """
    skip_commu: bool = True
    """检测并跳过交流"""

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


class ProduceSolutionManager:
    """培育方案管理器"""

    SOLUTIONS_DIR = "conf/produce"

    def __init__(self):
        """初始化管理器，确保目录存在"""
        os.makedirs(self.SOLUTIONS_DIR, exist_ok=True)

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

        return solutions

    def delete(self, id: str) -> None:
        """
        删除指定ID的培育方案

        :param id: 方案ID
        """
        file_path = self._find_file_path_by_id(id)
        if file_path:
            os.remove(file_path)

    def save(self, id: str, solution: ProduceSolution) -> None:
        """
        保存培育方案

        :param id: 方案ID
        :param solution: 方案对象
        """
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