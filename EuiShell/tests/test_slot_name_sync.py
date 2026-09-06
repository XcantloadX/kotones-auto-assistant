"""QML 与 Python 常量同步测试。"""
import re

from euishell import paths
from euishell.plugin import SlotName


def test_qml_slot_name_sync() -> None:
    """SlotName.qml 中的 slot 名称必须与 Python SlotName 一致。"""
    text = (paths.QML_MODULE_DIR / 'SlotName.qml').read_text(encoding='utf-8')
    qml_names = set(re.findall(r'"(\w+\.\w+)"', text))
    python_names = set(SlotName.ALL)
    assert qml_names == python_names, (
        f'QML/Python slot 名称不一致: qml={qml_names}, python={python_names}'
    )
