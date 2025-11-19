import os
import platform
from kotonebot.errors import UserFriendlyError


class KaaError(Exception):
    pass

class KaaUserFriendlyError(UserFriendlyError, KaaError):
    def __init__(self, message: str, help_link: str):
        self.message = message
        """用户友好的错误信息"""
        self.help_link = help_link
        """此错误的帮助链接"""
        super().__init__(message, [
            (0, '打开帮助', lambda: os.startfile(help_link)),
            (1, '知道了', lambda: None)
        ])

    def __str__(self):
        return f'【发生错误】{self.message}。访问 {self.help_link} 以获取更多帮助。'

class ServiceError(KaaUserFriendlyError):
    """Base class for service-related errors."""
    def __init__(self, message: str, help_link: str):
        super().__init__(message, help_link)

class UpdateServiceError(ServiceError):
    """Base class for update service errors."""
    pass

class UpdateFetchListError(UpdateServiceError):
    def __init__(self, reason: str):
        super().__init__(
            f'Failed to fetch version list: {reason}',
            '' # TODO
        )

class CompatibilityError(UpdateServiceError):
    def __init__(self, launcher_version: str, target_version: str):
        super().__init__(
            f"❌ 版本兼容性错误\n\n"
            f"启动器版本: {launcher_version}\n"
            f"要安装的版本: {target_version}\n\n"
            f"v2025.9b1 及以上版本需要**启动器 v0.5.0*** 或更高版本支持。\n"
            f"请先升级启动器到 v0.5.0 以上版本。",
            ''
        )

class UpdateInstallError(UpdateServiceError):
    def __init__(self, reason: str):
        super().__init__(
            f'Failed to start installation process: {reason}',
            '' # TODO
        )

class ProduceSolutionNotFoundError(KaaUserFriendlyError):
    def __init__(self, solution_id: str):
        self.solution_id = solution_id
        super().__init__(
            f'培育方案「{solution_id}」不存在，请检查设置是否正确。',
            'https://kdocs.cn/l/cetCY8mGKHLj?linkname=saPrDAmMd4'
        )

class ProduceSolutionInvalidError(KaaUserFriendlyError):
    def __init__(self, solution_id: str, file_path: str, reason: Exception):
        self.solution_id = solution_id
        self.reason = reason
        super().__init__(
            f'培育方案「{solution_id}」（路径 {file_path}）存在无效配置，载入失败。',
            'https://kdocs.cn/l/cetCY8mGKHLj?linkname=xnLUW1YYKz'
        )

class IdolCardNotFoundError(KaaUserFriendlyError):
    def __init__(self, skin_id: str):
        self.skin_id = skin_id
        super().__init__(
            f'未找到 ID 为「{skin_id}」的偶像卡。请检查游戏内偶像皮肤与培育方案中偶像皮肤是否一致。',
            'https://kdocs.cn/l/cetCY8mGKHLj?linkname=cySASqoPGj'
        )

class LauncherNotFoundError(KaaUserFriendlyError):
    def __init__(self):
        super().__init__(
            '未找到启动器「kaa.exe」，请确认是否正确放置在根目录。',
            'https://kdocs.cn/l/cetCY8mGKHLj?linkname=jpzb09rLTS'
        )

class ElevationRequiredError(KaaUserFriendlyError):
    def __init__(self):
        super().__init__(
            '请以管理员身份运行 kaa。',
            'https://www.kdocs.cn/l/cetCY8mGKHLj?linkname=qOqulS4KeX'
        )

class GameUpdateNeededError(KaaUserFriendlyError):
    def __init__(self):
        super().__init__(
            '游戏本体需要更新。kaa 暂不支持自动更新，请前往 Play Store 手动更新游戏。',
            'https://www.baidu.com/s?wd=%E5%BF%AB%E5%8E%BB%E6%9B%B4%E6%96%B0%E6%B8%B8%E6%88%8F%E5%95%8A%EF%BC%8C%E8%BF%98%E7%82%B9%E4%BB%80%E4%B9%88%E6%89%93%E5%BC%80%E5%B8%AE%E5%8A%A9'
        )

class NoProduceSolutionSelectedError(KaaUserFriendlyError):
    def __init__(self):
        super().__init__(
            '未选择培育方案。请前往「设置」，在「当前使用的培育方案」选择一个培育方案后再重新运行。',
            'https://www.kdocs.cn/l/cetCY8mGKHLj?linkname=LasxpznR6b'
        )

class DmmGameLaunchError(KaaUserFriendlyError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(
            f'绕过 DMM 启动器失败，原因：{reason}',
            'https://www.kdocs.cn/l/cetCY8mGKHLj?linkname=pSw7QcH1Kx'
        )

class WindowsOnlyError(KaaUserFriendlyError):
    def __init__(self, feature_name: str):
        super().__init__(
            f'此功能（{feature_name}）仅在 Windows 上可用。当前系统为 {platform.system()}。请不要使用此功能，或在 Windows 上运行 kaa。',
            'https://www.kdocs.cn/l/cetCY8mGKHLj?linkname=LbvACPfiCw'
        )