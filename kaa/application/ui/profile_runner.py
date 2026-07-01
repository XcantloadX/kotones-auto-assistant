"""ProfileRunner — 单个 profile 的 Blocks + Kaa 生命周期管理。

每个 ProfileRunner 实例对应一个 profile tab，
管理其独立的 Kaa、KaaFacade 和 gr.Blocks，并挂载到共享 FastAPI 服务器。
"""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gradio as gr
    from fastapi import FastAPI
    from kaa.application.ui.facade import KaaFacade
    from kaa.main.kaa import Kaa

logger = logging.getLogger(__name__)

_blocks_lock = __import__('threading').Lock()


class ProfileRunner:
    """管理一个 profile 的 Blocks + Kaa 生命周期。"""

    def __init__(self, profile_name: str, mount_path: str, server_app: 'FastAPI'):
        """
        :param profile_name: 配置名称
        :param mount_path: 挂载路径，如 "/p1"
        :param server_app: 共享 FastAPI 应用
        """
        self.profile_name = profile_name
        self.mount_path = mount_path
        self.server_app = server_app
        self._blocks: gr.Blocks | None = None
        self._facade: KaaFacade | None = None
        self._kaa: Kaa | None = None
        self._mounted = False

    @property
    def facade(self) -> 'KaaFacade | None':
        return self._facade

    @property
    def kaa(self) -> 'Kaa | None':
        return self._kaa

    @property
    def blocks(self) -> 'gr.Blocks | None':
        return self._blocks

    def mount(self) -> None:
        """创建 Kaa、Facade、Blocks 并挂载到共享 FastAPI。"""
        if self._mounted:
            return

        # 创建 Kaa 实例（不自动加载配置，由 run_tasks/start_tasks 线程自行注入）
        from kaa.main.kaa import Kaa
        self._kaa = Kaa(profile_name=self.profile_name)
        logger.info("ProfileRunner: Kaa created for '%s'", self.profile_name)

        # 创建 Facade
        from kaa.application.ui.facade import KaaFacade
        self._facade = KaaFacade(self._kaa, profile_name=self.profile_name)

        # 创建 Blocks
        from kaa.main.gr import create_profile_blocks
        self._blocks = create_profile_blocks(self._facade)

        # 挂载到共享 FastAPI（加锁避免并发修改路由表）
        from gradio.routes import mount_gradio_app
        with _blocks_lock:
            self.server_app = mount_gradio_app(
                self.server_app,
                self._blocks,
                path=self.mount_path,
            )

        self._mounted = True
        logger.info("ProfileRunner: Blocks mounted at '%s'", self.mount_path)

    def unmount(self) -> None:
        """卸载 Blocks 并清理资源。"""
        if not self._mounted:
            return

        # 停止 Kaa
        if self._kaa is not None:
            try:
                self._kaa.stop()
            except Exception:
                logger.exception("ProfileRunner: error stopping Kaa for '%s'", self.profile_name)

        self._blocks = None
        self._facade = None
        self._kaa = None
        self._mounted = False
        logger.info("ProfileRunner: unmounted '%s' from '%s'", self.profile_name, self.mount_path)

    def run_tasks(self) -> None:
        """在当前线程运行所有任务。"""
        if self._kaa is not None:
            self._kaa.run_all()

    def start_tasks(self) -> None:
        """异步启动所有任务（Kaa.start 自动注入 kaa_context 到 worker 线程）。"""
        if self._kaa is not None:
            self._kaa.start_all()

    @property
    def is_running(self) -> bool:
        from kotonebot.errors import ContextNotInitializedError
        try:
            return self._kaa is not None and self._kaa.is_running
        except ContextNotInitializedError:
            return False
        except Exception:
            return False
