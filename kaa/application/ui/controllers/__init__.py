"""Python ↔ QML 桥接层控制器。

对标 IAA 的 iaa/application/qt/controllers/。
"""
from .tab_manager import TabManager
from .profile_store_backend import ProfileStoreBackend

__all__ = ["TabManager", "ProfileStoreBackend"]
