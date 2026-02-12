import re
import json
import subprocess
import sys
import html.parser
import urllib.parse
from typing import Callable, List
from dataclasses import dataclass
from request import get, HTTPError
from importlib.metadata import version, PackageNotFoundError

PYTHON_EXECUTABLE = sys.executable
DEFAULT_PIP_SERVER = "https://pypi.org/simple"
# PEP 440 version regex (simplified from the official pattern)
VERSION_PATTERN = r"""
    v?
    (?:(?P<epoch>[0-9]+)!)?                           # epoch
    (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
    (?P<pre>                                          # pre-release
        [-_\.]?
        (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
        [-_\.]?
        (?P<pre_n>[0-9]+)?
    )?
    (?P<post>                                         # post release
        (?:-(?P<post_n1>[0-9]+))
        |
        (?:
            [-_\.]?
            (?P<post_l>post|rev|r)
            [-_\.]?
            (?P<post_n2>[0-9]+)?
        )
    )?
    (?P<dev>                                          # dev release
        [-_\.]?
        (?P<dev_l>dev)
        [-_\.]?
        (?P<dev_n>[0-9]+)?
    )?
    (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)?            # local version
"""
_VERSION_REGEX = re.compile(r"^\s*(?:" + VERSION_PATTERN + r")\s*$", re.VERBOSE | re.IGNORECASE)


def _normalize_pre_label(label: str) -> str:
    label = label.lower()
    if label in {"alpha", "a"}:
        return "a"
    if label in {"beta", "b"}:
        return "b"
    if label in {"rc", "c", "pre", "preview"}:
        return "rc"
    return label


@dataclass
class Version:
    """版本信息"""
    version_str: str
    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: str = ""
    prerelease_num: int = 0
    
    def __post_init__(self):
        """初始化后解析版本号"""
        self._parse_version()
    
    def _parse_version(self):
        """解析版本号字符串（尽量遵循 PEP 440）"""
        raw = self.version_str.strip()
        version_str = raw.lower().lstrip('v')

        # 使用 PEP 440 兼容的正则解析
        m = _VERSION_REGEX.match(version_str)
        if m:
            # 解析 release 段
            release = m.group('release')
            if release:
                parts = [int(p) for p in release.split('.')]
                self.major = parts[0] if len(parts) > 0 else 0
                self.minor = parts[1] if len(parts) > 1 else 0
                self.patch = parts[2] if len(parts) > 2 else 0

            # 处理 dev / pre / post（只保留一种标记用于比较与过滤）
            if m.group('dev') is not None:
                # 开发版视为预发布
                self.prerelease = 'dev'
                self.prerelease_num = int(m.group('dev_n') or 0)
            elif m.group('pre') is not None:
                self.prerelease = _normalize_pre_label(m.group('pre_l') or '')
                self.prerelease_num = int(m.group('pre_n') or 0)
            elif m.group('post') is not None:
                # post 版本：比正式版更高
                self.prerelease = 'post'
                # 两种 post 表达方式择其一
                post_n = m.group('post_n1') or m.group('post_n2') or 0
                self.prerelease_num = int(post_n)
            else:
                self.prerelease = ''
                self.prerelease_num = 0
            return

        # 回退：简单解析
        version_match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?', version_str)
        if version_match:
            self.major = int(version_match.group(1))
            self.minor = int(version_match.group(2)) if version_match.group(2) else 0
            self.patch = int(version_match.group(3)) if version_match.group(3) else 0
        
        prerelease_match = re.search(r'(a|b|c|rc|alpha|beta|pre|preview|dev|post)\s*([0-9]*)', version_str)
        if prerelease_match:
            self.prerelease = _normalize_pre_label(prerelease_match.group(1))
            self.prerelease_num = int(prerelease_match.group(2)) if prerelease_match.group(2) else 0
    
    def __lt__(self, other):
        """版本比较"""
        if not isinstance(other, Version):
            return NotImplemented
        
        # 比较主版本号
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        
        # 比较预发布/后发布顺序（dev < a < b < rc < final < post）
        prerelease_order = {'dev': 0, 'a': 1, 'b': 2, 'rc': 3, '': 4, 'post': 5}
        self_order = prerelease_order.get(self.prerelease, 4)
        other_order = prerelease_order.get(other.prerelease, 4)
        
        if self_order != other_order:
            return self_order < other_order
        
        # 同类型比较数字
        if self.prerelease == other.prerelease:
            return self.prerelease_num < other.prerelease_num
        
        return False
    
    def __eq__(self, other):
        """版本相等比较"""
        if not isinstance(other, Version):
            return NotImplemented
        
        return (self.major == other.major and 
                self.minor == other.minor and 
                self.patch == other.patch and
                self.prerelease == other.prerelease and
                self.prerelease_num == other.prerelease_num)
    
    def __repr__(self):
        return f"Version('{self.version_str}')"

    def __str__(self):
        return self.version_str

@dataclass
class PackageVersion:
    """包版本信息"""
    version: Version
    url: str


class PyPIHTMLParser(html.parser.HTMLParser):
    """解析PyPI HTML响应的解析器"""
    
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = None
        
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            # 提取href属性
            for attr_name, attr_value in attrs:
                if attr_name == 'href':
                    self.current_href = attr_value
                    break
    
    def handle_data(self, data):
        if self.current_href:
            self.current_text = data.strip()
    
    def handle_endtag(self, tag):
        if tag == 'a' and self.current_href and self.current_text:
            self.links.append((self.current_text, self.current_href))
            self.current_href = None
            self.current_text = None


def normalize_package_name(package_name: str) -> str:
    """
    标准化包名，将 _, -, . 字符视为相等
    """
    return re.sub(r'[_.-]', '-', package_name.lower())


def extract_version_from_filename(filename: str) -> str:
    """
    从文件名中提取版本号
    
    例如: beautifulsoup4-4.13.0b2-py3-none-any.whl -> 4.13.0b2
    """
    # 匹配版本号模式
    version_pattern = r'^[^-]+-([^-]+?)(?:-py\d+)?(?:-none-any)?\.(?:whl|tar\.gz|zip)$'
    match = re.match(version_pattern, filename)
    if match:
        return match.group(1)
    
    # 备用模式：查找版本号
    version_match = re.search(r'-(\d+\.\d+(?:\.\d+)?(?:[a-zA-Z0-9]*))', filename)
    if version_match:
        return version_match.group(1)
    
    return "unknown"

ExecuteCommandFunc = Callable[[str], tuple[int, str]]

class PipPackage:
    def __init__(
        self,
        package_name: str,
        *,
        server_url: str = DEFAULT_PIP_SERVER,
        extra_index_urls: list[str] | None = None,
        trusted_host: list[str] | None = None,
        execute_command: ExecuteCommandFunc | None = None,
    ):
        self.package_name = package_name
        self.server_url = server_url
        self.extra_index_urls = extra_index_urls or []
        self.trusted_hosts = trusted_host
        self.normalized_name = normalize_package_name(package_name)
        self.execute_command: ExecuteCommandFunc = execute_command or self.__exec_command

    def __exec_command(self, command: str) -> tuple[int, str]:
        result = subprocess.run(command, check=True, capture_output=True)
        return result.returncode, result.stdout.decode('utf-8')

    def call_pip(self, args: list[str], *, with_default_args: bool = True) -> tuple[int, str]:
        """
        调用 pip 命令
        """
        return self.execute_command(f'"{PYTHON_EXECUTABLE}" -m pip {" ".join(args)}')

    def install(self, version: str) -> bool:
        args = [
            'install',
            f'{self.package_name}=={version}',
            '--index-url', self.server_url,
        ]
        for url in self.extra_index_urls:
            args += ['--extra-index-url', url]
        retcode, _ = self.call_pip(args)
        if retcode != 0:
            raise RuntimeError(f'安装失败，返回码: {retcode}')
        return retcode == 0
    
    def uninstall(self) -> bool:
        retcode, _ = self.call_pip(['uninstall', self.package_name, '-y'])
        if retcode != 0:
            raise RuntimeError(f'卸载失败，返回码: {retcode}')
        return retcode == 0

    def is_installed(self) -> bool:
        try:
            version(self.package_name)
            return True
        except PackageNotFoundError:
            return False

    def local_version(self) -> Version | None:
        try:
            v = version(self.package_name)
            return Version(v)
        except PackageNotFoundError:
            return None
        except Exception as e:
            raise RuntimeError(f'获取本地版本失败，包名: {self.package_name}') from e
            return None
    
    def list_versions(self, *, pre: bool = True) -> List[PackageVersion]:
        """
        列出所有远程版本。

        :param pre: 是否包含预发布版本。
        :return: 版本列表。
        """
        args = [
            'index',
            'versions',
            self.package_name,
            '--json',
            '--pre' if pre else '',
            '--index-url', self.server_url,
        ]
        for url in self.extra_index_urls:
            args += ['--extra-index-url', url]
        retcode, output = self.call_pip(args)
        if retcode != 0:
            raise RuntimeError(f'获取版本列表失败，返回码: {retcode}')
        ret = json.loads(output)
        versions = ret['versions']
        return [PackageVersion(Version(version), '') for version in versions]

    def latest_version(self, *, pre: bool = True) -> Version | None:
        """
        获取最新版本。

        :param pre: 是否包含预发布版本。
        :return: 最新版本。
        """
        versions = self.list_versions(pre=pre)
        return versions[0].version if versions else None
    
    def install_from_file(self, file_path: str, *, upgrade: bool = True) -> bool:
        """
        从文件安装。

        :param file_path: 文件路径。
        :param upgrade: 是否升级。
        :return: 是否成功。
        """
        args = [
            'install',
            file_path,
            '--index-url', self.server_url,
        ]
        for url in self.extra_index_urls:
            args += ['--extra-index-url', url]
        if upgrade:
            args.append('--upgrade')
        retcode, _ = self.call_pip(args)
        if retcode != 0:
            raise RuntimeError(f'安装失败，返回码: {retcode}')
        return retcode == 0
    
    def install_from_folder(self, folder_path: str, *, upgrade: bool = True) -> bool:
        """
        从文件夹安装。

        :param folder_path: 文件夹路径。
        :param upgrade: 是否升级。
        :return: 是否成功。
        """
        args = [
            'install',
            '--find-links', folder_path,
            self.package_name,
            # '--index-url', self.server_url,
            '--no-index',
        ]
        if upgrade:
            args.append('--upgrade')
        retcode, _ = self.call_pip(args)
        if retcode != 0:
            raise RuntimeError(f'安装失败，返回码: {retcode}')
        return retcode == 0
