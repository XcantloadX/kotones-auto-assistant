"""测试 v5 到 v6 的配置迁移脚本"""
import unittest
import tempfile
import os
import json
import shutil
from typing import Any

from kaa.config.migrations._v5_to_v6 import migrate


class TestMigrationV5ToV6(unittest.TestCase):
    """测试 v5 到 v6 的配置迁移"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """清理测试环境"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)

    def test_migrate_empty_config(self):
        """测试空配置的迁移"""
        user_config = {}
        result = migrate(user_config)
        self.assertIsNone(result)

    def test_migrate_no_options(self):
        """测试没有 options 的配置"""
        user_config = {"backend": {"type": "mumu12"}}
        result = migrate(user_config)
        self.assertIsNone(result)

    def test_migrate_no_produce_config(self):
        """测试没有 produce 配置的情况"""
        user_config = {"options": {"purchase": {"enabled": False}}}
        result = migrate(user_config)
        self.assertIsNone(result)

    def test_migrate_already_v6_format(self):
        """测试已经是 v6 格式的配置"""
        user_config = {
            "options": {
                "produce": {
                    "enabled": True,
                    "selected_solution_id": "test-id",
                    "produce_count": 1
                }
            }
        }
        result = migrate(user_config)
        self.assertIsNone(result)

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
            "skip_commu": False
        }

        user_config = {"options": {"produce": old_produce_config}}

        # 执行迁移
        result = migrate(user_config)

        # 验证结果
        self.assertIsNotNone(result)
        assert result is not None # make pylance happy
        self.assertIn("已将培育配置迁移到新的方案系统", result)

        # 验证新配置格式
        new_produce_config = user_config["options"]["produce"]
        self.assertEqual(new_produce_config["enabled"], True)
        self.assertEqual(new_produce_config["produce_count"], 3)
        self.assertIsNotNone(new_produce_config["selected_solution_id"])

        # 验证方案文件是否创建
        solutions_dir = "conf/produce"
        self.assertTrue(os.path.exists(solutions_dir))
        
        # 查找创建的方案文件
        solution_files = [f for f in os.listdir(solutions_dir) if f.endswith('.json')]
        self.assertEqual(len(solution_files), 1)

        # 验证方案文件内容
        solution_file = os.path.join(solutions_dir, solution_files[0])
        with open(solution_file, 'r', encoding='utf-8') as f:
            solution_data = json.load(f)

        self.assertEqual(solution_data["type"], "produce_solution")
        self.assertEqual(solution_data["name"], "默认方案")
        self.assertEqual(solution_data["description"], "从旧配置迁移的默认培育方案")
        
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
        self.assertEqual(produce_data["actions_order"], ["recommended", "visual", "vocal"])
        self.assertEqual(produce_data["recommend_card_detection_mode"], "strict")
        self.assertEqual(produce_data["use_ap_drink"], True)
        self.assertEqual(produce_data["skip_commu"], False)

    def test_migrate_v5_to_v6_with_defaults(self):
        """测试使用默认值的 v5 到 v6 迁移"""
        # 创建最小的 v5 格式配置
        old_produce_config = {"enabled": False}
        user_config = {"options": {"produce": old_produce_config}}

        # 执行迁移
        result = migrate(user_config)

        # 验证结果
        self.assertIsNotNone(result)

        # 验证新配置格式
        new_produce_config = user_config["options"]["produce"]
        self.assertEqual(new_produce_config["enabled"], False)
        self.assertEqual(new_produce_config["produce_count"], 1)
        self.assertIsNotNone(new_produce_config["selected_solution_id"])

        # 验证方案文件内容使用了默认值
        solutions_dir = "conf/produce"
        solution_files = [f for f in os.listdir(solutions_dir) if f.endswith('.json')]
        solution_file = os.path.join(solutions_dir, solution_files[0])
        
        with open(solution_file, 'r', encoding='utf-8') as f:
            solution_data = json.load(f)

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
            "support_card_sets": [4, 5, 6]
        }
        user_config = {"options": {"produce": old_produce_config}}

        # 执行迁移
        result = migrate(user_config)

        # 验证结果
        self.assertIsNotNone(result)

        # 验证方案文件内容只使用了第一个值
        solutions_dir = "conf/produce"
        solution_files = [f for f in os.listdir(solutions_dir) if f.endswith('.json')]
        solution_file = os.path.join(solutions_dir, solution_files[0])
        
        with open(solution_file, 'r', encoding='utf-8') as f:
            solution_data = json.load(f)

        produce_data = solution_data["data"]
        self.assertEqual(produce_data["idol"], "idol1")
        self.assertEqual(produce_data["memory_set"], 1)
        self.assertEqual(produce_data["support_card_set"], 4)


if __name__ == '__main__':
    unittest.main()
