"""TaskTogglesModel / ProgressAggregator 单元测试。"""
from PySide6.QtCore import Qt

from euishell.bridges.progress import ProgressAggregator
from euishell.controllers.task_toggles_model import TaskTogglesModel

from .conftest import DummyTaskToggles


def test_toggles_model_roles() -> None:
    source = DummyTaskToggles()
    model = TaskTogglesModel(source)
    assert model.rowCount() == 3
    assert model.data(model.index(0, 0), model.KeyRole) == 'a'
    assert model.data(model.index(0, 0), model.LabelRole) == '开关a'
    assert model.data(model.index(0, 0), model.EnabledRole) is True
    assert model.roleNames()[model.KeyRole] == b'key'


def test_toggles_model_refresh() -> None:
    source = DummyTaskToggles()
    model = TaskTogglesModel(source)
    source.set_enabled('a', False)
    assert model.data(model.index(0, 0), model.EnabledRole) is True
    model.refresh()
    assert model.data(model.index(0, 0), model.EnabledRole) is False


def test_progress_aggregator_flush_throttle() -> None:
    agg = ProgressAggregator(flush_interval=3600)
    agg.update('a.bin', 50, 100)
    # 首次 flush（_last_flush 未设置）总是放行
    items = agg.flush()
    assert items is not None and len(items) == 1
    item = items[0]
    assert item.file_name == 'a.bin'
    assert item.percent == 50.0
    # 刚 flush 过且无新数据时不再导出
    agg.update('a.bin', 60, 100)
    assert agg.flush() is None
    # force_flush 无视节流间隔
    items = agg.force_flush()
    assert items is not None
    assert items[0].percent == 60.0
    # 清空后无新数据
    agg.clear()
    assert agg.force_flush() is None


def test_progress_aggregator_zero_total() -> None:
    agg = ProgressAggregator()
    agg.update('b.bin', 10, 0)
    items = agg.force_flush()
    assert items is not None
    assert items[0].percent == 0.0
    assert '—' in items[0].size_text


def test_qt_user_role_collision() -> None:
    """模型角色 id 不得与 Qt 内置角色冲突。"""
    assert TaskTogglesModel.KeyRole >= Qt.ItemDataRole.UserRole
