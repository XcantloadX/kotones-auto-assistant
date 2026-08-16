import copy
import logging

from kaa.application.services.config_service import (
    ConfigService,
    _set_dict_path,
    _get_dict_path,
)
from kaa.config.schema import KaaConfig
from kaa.config.validation import ConfigIssue

logger = logging.getLogger(__name__)


class ConfigDraft:
    """SettingsPage 草稿：base（显示快照）+ dirty（编辑覆盖层）。

    - set() 只进 _dirty，不碰 live config 和磁盘。
    - commit() 重读 live 作 base，只叠 dirty 路径，整体校验后再替换 live。
    - validate_view() 实时校验 base+dirty 合并视图，供 UI 内联展示（不提交）。
    - refresh() 由 configChanged 触发，刷 _base 保留 _dirty。
    """

    def __init__(self, cs: ConfigService):
        self._cs = cs
        self._base: dict = {}
        self._base_shared: dict = {}
        self._dirty: dict = {}
        self._last_issues: list[ConfigIssue] = []
        self.refresh()

    @property
    def last_issues(self) -> list[ConfigIssue]:
        """最近一次 commit 失败的结构化校验问题；无失败时为空列表。"""
        return list(self._last_issues)

    def refresh(self):
        """外部变更（configChanged）时刷新 _base 快照。"""
        self._base = self._cs.get_config().model_dump(mode='json')
        self._base_shared = self._cs.get_shared().model_dump(mode='json')

    def view(self) -> dict:
        """base + dirty 合并后的视图，供 FormBinder.data 显示。"""
        merged = copy.deepcopy(self._base)
        for path, value in self._dirty.items():
            _set_dict_path(merged, path, value)
        return merged

    def view_shared(self) -> dict:
        """返回缓存的 shared 配置（不读盘）。"""
        return self._base_shared

    def get(self, path: str):
        """读取字段值：dirty 优先，fallback 到 base。"""
        if path in self._dirty:
            return self._dirty[path]
        return _get_dict_path(self._base, path)

    def set(self, path: str, value) -> None:
        """编辑字段：只进 dirty，不碰 live。"""
        self._dirty[path] = value

    def is_dirty(self) -> bool:
        return len(self._dirty) > 0

    def validate_view(self) -> list[ConfigIssue]:
        """校验 base + dirty 合并后的视图（不提交、不写盘）。

        供设置页实时展示校验问题；Pydantic 结构错误会以 error 级 issue 返回，
        保证 UI 始终能拿到可展示的错误信息。
        """
        try:
            candidate = KaaConfig.model_validate(self.view())
            return self._cs.collect_issues(candidate)
        except Exception as e:
            logger.warning("Config draft view validation failed: %s", e)
            return [ConfigIssue(
                severity='error',
                field=None,
                message=f"配置结构无效：{e}",
            )]

    def commit(self) -> bool:
        """合并 dirty 到 live，整体校验，写盘。

        先将 live config 序列化为 dict，叠 dirty 路径后再反序列化回模型。
        这样可以正确触发 Pydantic discriminated union 的重新构造，
        避免切换 backend.lifecycle.type 后成员类型不变导致的字段不兼容问题。
        校验失败时 live 不变，结构化问题保存在 last_issues 供 UI 展示。
        """
        data = self._cs.get_config().model_dump(mode='json')
        for path, value in self._dirty.items():
            _set_dict_path(data, path, value)
        try:
            candidate = KaaConfig.model_validate(data)
        except Exception:
            logger.exception("ConfigDraft commit validation failed")
            self._last_issues = []
            return False
        issues = self._cs.collect_issues(candidate)
        errors = [i for i in issues if i.severity == 'error']
        if errors:
            # 业务校验失败是预期的用户输入问题，不是 bug：
            # 仅 warning 记录（不触发错误上报），并把结构化问题透出给 UI。
            logger.warning("Config validation rejected on commit: %s",
                           [i.message for i in errors])
            self._last_issues = issues
            return False
        self._cs.set_config(candidate)
        self._cs.save()
        self._dirty.clear()
        self._last_issues = []
        return True

    def discard(self) -> None:
        """丢弃所有未保存编辑。"""
        self._dirty.clear()