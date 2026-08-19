"""ADB 连接配置（TcpConnection ip/port）校验规则测试。"""

from unittest import TestCase

from kaa.config.base_config import TcpConnection
from kaa.config.schema import KaaConfig
from kaa.config.validation import validate_profile_config


def _build_config(ip: str, port: int = 5555) -> KaaConfig:
    """构造一个 custom 后端 + tcp 连接的 KaaConfig。"""
    return KaaConfig(backend={
        'lifecycle': {'type': 'custom'},
        'connection': {'type': 'tcp', 'ip': ip, 'port': port},
    })


class TestTcpConnectionIpContainsPort(TestCase):
    """TcpConnection._ip_contains_port 判定逻辑。"""

    def test_plain_ip(self):
        self.assertFalse(TcpConnection(type='tcp', ip='127.0.0.1')._ip_contains_port())

    def test_hostname(self):
        self.assertFalse(TcpConnection(type='tcp', ip='localhost')._ip_contains_port())

    def test_ip_with_port(self):
        self.assertTrue(TcpConnection(type='tcp', ip='127.0.0.1:16384')._ip_contains_port())

    def test_hostname_with_port(self):
        self.assertTrue(TcpConnection(type='tcp', ip='localhost:5555')._ip_contains_port())

    def test_ipv6_not_misjudged(self):
        self.assertFalse(TcpConnection(type='tcp', ip='::1')._ip_contains_port())
        self.assertFalse(TcpConnection(type='tcp', ip='fe80::1')._ip_contains_port())
        self.assertFalse(TcpConnection(type='tcp', ip='2001:db8::1')._ip_contains_port())


class TestConnectionIpValidation(TestCase):
    """validate_profile_config 对 ip 携带端口的拦截。"""

    def test_bad_ip_raises_error_issue(self):
        issues = validate_profile_config(_build_config(ip='127.0.0.1:16384'))
        errors = [i for i in issues if i.severity == 'error' and i.field == 'backend.connection.ip']
        self.assertEqual(len(errors), 1)
        self.assertIn('16384', errors[0].message)

    def test_good_ip_no_issue(self):
        issues = validate_profile_config(_build_config(ip='127.0.0.1', port=16384))
        self.assertEqual([i for i in issues if i.field == 'backend.connection.ip'], [])