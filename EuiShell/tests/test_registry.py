"""ShellRegistry 注册校验与 JSON 视图测试。"""
import json

import pytest

from pathlib import Path

from euishell.plugin import (
    PageSpec,
    SectionSpec,
    ShellRegistry,
    SlotItemSpec,
    SlotName,
    SlotSpec,
)
from euishell.exceptions import RegistrationError


def _page(page_id: str, **kw: str) -> PageSpec:
    return PageSpec(id=page_id, title=page_id, qml_file=Path(__file__), **kw)


def test_register_slot_rejects_unknown_name() -> None:
    registry = ShellRegistry()
    with pytest.raises(RegistrationError):
        registry.register_slot(SlotSpec(name='not.a.slot', items=[]))


def test_register_slot_rejects_duplicate() -> None:
    registry = ShellRegistry()
    registry.register_slot(SlotSpec(name=SlotName.ABOUT_EXTRA, items=[]))
    with pytest.raises(RegistrationError):
        registry.register_slot(SlotSpec(name=SlotName.ABOUT_EXTRA, items=[]))


def test_register_page_rejects_duplicate_id() -> None:
    registry = ShellRegistry()
    registry.register_page(_page('produce'))
    with pytest.raises(RegistrationError):
        registry.register_page(_page('produce'))


def test_register_fullscreen_page_rejects_duplicate_id() -> None:
    registry = ShellRegistry()
    registry.register_fullscreen_page(_page('browser'))
    with pytest.raises(RegistrationError):
        registry.register_page(_page('browser'))


def test_register_section_rejects_duplicate_id() -> None:
    registry = ShellRegistry()
    section = SectionSpec(id='daily', title='日常', qml_file=Path(__file__))
    registry.register_settings_section(section)
    with pytest.raises(RegistrationError):
        registry.register_settings_section(section)


def test_slot_items_json_uses_file_url() -> None:
    registry = ShellRegistry()
    registry.register_slot(SlotSpec(
        name=SlotName.ABOUT_EXTRA,
        items=[SlotItemSpec(qml_file=Path(__file__), controllerRole='extra')],
    ))
    items = json.loads(registry.slotItemsJson(SlotName.ABOUT_EXTRA))
    assert items[0]['url'].startswith('file:///')
    assert items[0]['controllerRole'] == 'extra'
    assert json.loads(registry.slotItemsJson(SlotName.OVERVIEW)) == []


def test_custom_pages_json_roundtrip() -> None:
    registry = ShellRegistry()
    registry.register_page(PageSpec(
        id='produce', title='方案', qml_file=Path(__file__), after='settings',
    ))
    pages = json.loads(registry.customPagesJson())
    assert pages == [{
        'id': 'produce', 'title': '方案',
        'url': pages[0]['url'], 'after': 'settings',
    }]
    assert pages[0]['url'].startswith('file:///')


def test_global_controller_lookup() -> None:
    registry = ShellRegistry()

    class _Ctrl:
        pass

    ctrl = _Ctrl()
    registry.set_global_controllers({'game': ctrl})  # type: ignore[dict-item]
    assert registry.globalController('game') is ctrl
    assert registry.globalController('missing') is None


def test_about_json() -> None:
    registry = ShellRegistry()
    registry.set_app_info('App', [])
    about = json.loads(registry.aboutJson())
    assert about == {'appName': 'App', 'links': []}
