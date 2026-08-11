"""测试 v5 到 v6 的配置迁移（ProfileV5ToV6 步骤）。"""
import unittest
import tempfile
import json
import shutil
from pathlib import Path

from kaa.config.migrations import ProfileV5ToV6
from kaa.config.migration import MigrationContext


class TestMigrationV5ToV6(unittest.TestCase):
    """测试 v5 到 v6 的配置迁移"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时目录作为 conf 根目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir)
        self.ctx = MigrationContext(config_dir=self.config_dir)
        self.step = ProfileV5ToV6()

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)

    def _write_config(self, data: dict) -> None:
        """写入 conf/config.json"""
        (self.config_dir / 'config.json').write_text(
            json.dumps(data, ensure_ascii=False, indent=4), encoding='utf-8')

    def _read_config(self) -> dict:
        """读取 conf/config.json"""
        return json.loads((self.config_dir / 'config.json').read_text(encoding='utf-8'))

    def test_empty_config(self):
        """测试空配置（无 user_configs）"""
        self._write_config({'version': 5, 'user_configs': []})
        self.assertTrue(self.step.check_needed(self.ctx))

        self.step.apply(self.ctx)

        self.assertEqual(self._read_config()['version'], 6)
        # 没有需要迁移的配置，不应产生消息
        self.assertEqual(self.ctx.messages, [])

    def test_no_options(self):
        """测试没有 options 的配置"""
        self._write_config({
            'version': 5,
            'user_configs': [{'name': 'default', 'backend': {'type': 'mumu12'}}],
        })
        self.step.apply(self.ctx)

        self.assertEqual(self._read_config()['version'], 6)
        self.assertEqual(self.ctx.messages, [])

    def test_no_produce_config(self):
        """测试没有 produce 配置的情况"""
        self._write_config({
            'version': 5,
            'user_configs': [{
                'name': 'default',
                'options': {'purchase': {'enabled': False}},
            }],
        })
        self.step.apply(self.ctx)

        self.assertEqual(self._read_config()['version'], 6)
        self.assertEqual(self.ctx.messages, [])

    def test_already_v6_format(self):
        """测试已经是 v6 格式（含 selected_solution_id）的配置不迁移"""
        self._write_config({
            'version': 5,
            'user_configs': [{
                'name': 'default',
                'options': {
                    'produce': {
                        'enabled': True,
                        'selected_solution_id': 'test-id',
                        'produce_count': 1,
                    },
                },
            }],
        })
        self.step.apply(self.ctx)

        # 已经是最新格式，不应被重复迁移
        self.assertEqual(self.ctx.messages, [])
        user_cfg = self._read_config()['user_configs'][0]
        self.assertEqual(
            user_cfg['options']['produce']['selected_solution_id'], 'test-id')

    def test_migrate_v5_to_v6_basic(self):
        """测试基本的 v5 到 v6 迁移"""
        # 创建 v5 格式的配置
        old_produce_config = {
            "enabled": True,
            "mode": "pro",
            "produce_count": 3,
            "idols": ["i_card-skin-fktn-3-000"],
            "memory_sets": [1],
            "support_card_sets": [2],
            "auto_set_memory": False,
            "auto_set_support_card": True,
            "use_pt_boost": True,
            "use_note_boost": False,
            "follow_producer": True,
            "self_study_lesson": "vocal",
            "prefer_lesson_ap": True,
            "actions_order": ["recommended", "visual", "vocal"],
            "recommend_card_detection_mode": "strict",
            "use_ap_drink": True,
            "skip_commu": False,
        }
        self._write_config({
            'version': 5,
            'user_configs': [{
                'name': 'default',
                'options': {'produce': old_produce_config},
            }],
        })

        # 执行迁移
        self.step.apply(self.ctx)

        # 验证消息
        self.assertEqual(len(self.ctx.messages), 1)
        self.assertIn("已将以下配置的培育参数迁移到方案系统", self.ctx.messages[0].text)

        # 验证新配置格式
        new_produce_config = (
            self._read_config()['user_configs'][0]['options']['produce'])
        self.assertEqual(new_produce_config["enabled"], True)
        self.assertEqual(new_produce_config["produce_count"], 3)
        self.assertIsNotNone(new_produce_config["selected_solution_id"])

        # 验证方案文件是否创建
        solutions_dir = self.config_dir / 'produce'
        self.assertTrue(solutions_dir.exists())

        # 查找创建的方案文件
        solution_files = [f for f in solutions_dir.iterdir() if f.suffix == '.json']
        self.assertEqual(len(solution_files), 1)

        # 验证方案文件内容
        solution_data = json.loads(solution_files[0].read_text(encoding='utf-8'))
        self.assertEqual(solution_data["type"], "produce_solution")
        self.assertEqual(solution_data["name"], "默认方案")
        self.assertEqual(solution_data["description"], "从旧配置迁移的默认培育方案")
        self.assertEqual(
            solution_data["id"], new_produce_config["selected_solution_id"])

        # 验证培育数据
        produce_data = solution_data["data"]
        self.assertEqual(produce_data["mode"], "pro")
        self.assertEqual(produce_data["idol"], "i_card-skin-fktn-3-000")
        self.assertEqual(produce_data["memory_set"], 1)
        self.assertEqual(produce_data["support_card_set"], 2)
        self.assertEqual(produce_data["auto_set_memory"], False)
        self.assertEqual(produce_data["auto_set_support_card"], True)
        self.assertEqual(produce_data["use_pt_boost"], True)
        self.assertEqual(produce_data["use_note_boost"], False)
        self.assertEqual(produce_data["follow_producer"], True)
        self.assertEqual(produce_data["self_study_lesson"], "vocal")
        self.assertEqual(produce_data["prefer_lesson_ap"], True)
        self.assertEqual(
            produce_data["actions_order"], ["recommended", "visual", "vocal"])
        self.assertEqual(produce_data["recommend_card_detection_mode"], "strict")
        self.assertEqual(produce_data["use_ap_drink"], True)
        self.assertEqual(produce_data["skip_commu"], False)

    def test_migrate_v5_to_v6_with_defaults(self):
        """测试使用默认值的 v5 到 v6 迁移"""
        # 创建最小的 v5 格式配置
        old_produce_config = {"enabled": False}
        self._write_config({
            'version': 5,
            'user_configs': [{
                'name': 'default',
                'options': {'produce': old_produce_config},
            }],
        })

        # 执行迁移
        self.step.apply(self.ctx)

        # 验证新配置格式
        new_produce_config = (
            self._read_config()['user_configs'][0]['options']['produce'])
        self.assertEqual(new_produce_config["enabled"], False)
        self.assertEqual(new_produce_config["produce_count"], 1)
        self.assertIsNotNone(new_produce_config["selected_solution_id"])

        # 验证方案文件内容使用了默认值
        solutions_dir = self.config_dir / 'produce'
        solution_files = [f for f in solutions_dir.iterdir() if f.suffix == '.json']
        solution_data = json.loads(solution_files[0].read_text(encoding='utf-8'))

        produce_data = solution_data["data"]
        self.assertEqual(produce_data["mode"], "regular")
        self.assertIsNone(produce_data["idol"])
        self.assertIsNone(produce_data["memory_set"])
        self.assertIsNone(produce_data["support_card_set"])
        self.assertEqual(produce_data["auto_set_memory"], False)
        self.assertEqual(produce_data["auto_set_support_card"], False)
        self.assertEqual(produce_data["self_study_lesson"], "dance")
        self.assertEqual(produce_data["skip_commu"], True)

    def test_migrate_v5_to_v6_multiple_idols_memory_support(self):
        """测试多个偶像、回忆、支援卡的迁移（只取第一个）"""
        old_produce_config = {
            "enabled": True,
            "idols": ["idol1", "idol2", "idol3"],
            "memory_sets": [1, 2, 3],
            "support_card_sets": [4, 5, 6],
        }
        self._write_config({
            'version': 5,
            'user_configs': [{
                'name': 'default',
                'options': {'produce': old_produce_config},
            }],
        })

        # 执行迁移
        self.step.apply(self.ctx)

        # 验证方案文件内容只使用了第一个值
        solutions_dir = self.config_dir / 'produce'
        solution_files = [f for f in solutions_dir.iterdir() if f.suffix == '.json']
        solution_data = json.loads(solution_files[0].read_text(encoding='utf-8'))

        produce_data = solution_data["data"]
        self.assertEqual(produce_data["idol"], "idol1")
        self.assertEqual(produce_data["memory_set"], 1)
        self.assertEqual(produce_data["support_card_set"], 4)


if __name__ == '__main__':
    unittest.main()
