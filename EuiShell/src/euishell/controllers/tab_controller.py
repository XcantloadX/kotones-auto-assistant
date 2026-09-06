"""TabController — 单个 Tab 的控制器聚合，暴露给 QML 的统一入口。"""
from PySide6.QtCore import Property, QObject, Signal, Slot

from euishell.bridges.log_bridge import LogBridge
from euishell.bridges.progress import ProgressBridge
from euishell.controllers.run_controller import RunController
from euishell.session import ShellSession, TabApi


class TabController(QObject):
    """聚合一个 Tab 的全部 QML 可访问控制器。

    惰性创建时机由 TabManager 控制（首次被 QML 访问时）；创建时即向
    session 注入 :class:`TabApi`，下游可开始推送进度等。
    """

    dirtyGuardsChanged = Signal()

    def __init__(self, session: ShellSession, parent: QObject | None = None) -> None:
        """
        :param session: 该 Tab 对应的下游会话
        :param parent: Qt 父对象
        """
        super().__init__(parent)
        self._session = session

        self.progress_bridge = ProgressBridge(self)
        self.log_bridge = LogBridge(self)
        # 捕获从 Tab 创建起的全部输出；QML LogPage 可再读历史缓冲
        self.log_bridge.install()

        session.attach_tab(TabApi(progress=self.progress_bridge, log_bridge=self.log_bridge))

        self._run_ctrl: RunController | None = None
        if session.task_control() is not None or session.task_toggles() is not None:
            self._run_ctrl = RunController(session.task_control(), session.task_toggles(), self)
        self._settings_ctrl = session.settings_controller()
        self._controllers = session.controllers()
        self._dirty_guards = session.dirty_guards()

    @Property(QObject, constant=True)
    def runCtrl(self) -> QObject | None:
        return self._run_ctrl

    @Property(QObject, constant=True)
    def progressCtrl(self) -> QObject:
        return self.progress_bridge

    @Property(QObject, constant=True)
    def logBridge(self) -> QObject:
        return self.log_bridge

    @Property(QObject, constant=True)
    def settingsCtrl(self) -> QObject | None:
        return self._settings_ctrl

    @Property('QVariantList', notify=dirtyGuardsChanged)  # type: ignore[arg-type]
    def dirtyGuards(self) -> list:
        return list(self._dirty_guards)

    @Slot(str, result='QVariant')  # type: ignore
    def controller(self, role: str) -> QObject | None:
        """按 role 返回该 Tab 的下游控制器。

        :param role: 控制器 role 名
        """
        return self._controllers.get(role)

    def destroy(self) -> None:
        """卸载日志捕获；session 生命周期由 TabManager 管理。"""
        try:
            self.log_bridge.close()
        except Exception:
            pass
