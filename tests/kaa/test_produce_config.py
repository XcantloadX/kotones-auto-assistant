import os
import json
import tempfile
import shutil
import uuid
from unittest import TestCase


from kaa.config.produce import (
    ProduceData, 
    ProduceSolution, 
    ProduceSolutionManager
)
from kaa.config.const import ProduceAction, RecommendCardDetectionMode
from kaa.errors import ProduceSolutionNotFoundError


class TestProduceData(TestCase):

    def test_produce_data_field_validation(self):
        """测试字段验证"""
        # 测试有效的 mode 值
        for mode in ['regular', 'pro', 'master']:
            data = ProduceData(mode=mode) # type: ignore[arg-type]
            self.assertEqual(data.mode, mode)
        
        # 测试有效的 self_study_lesson 值
        for lesson in ['dance', 'visual', 'vocal']:
            data = ProduceData(self_study_lesson=lesson) # type: ignore[arg-type]
            self.assertEqual(data.self_study_lesson, lesson)

    def test_produce_data_serialization(self):
        """测试序列化和反序列化"""
        # 创建测试数据
        data = ProduceData(
            mode='pro',
            idol='test_idol_123',
            memory_set=2,
            support_card_set=3,
            auto_set_memory=True,
            auto_set_support_card=True,
            use_pt_boost=True,
            use_note_boost=True,
            follow_producer=True,
            self_study_lesson='vocal',
            prefer_lesson_ap=True,
            actions_order=[ProduceAction.DANCE, ProduceAction.VOCAL],
            recommend_card_detection_mode=RecommendCardDetectionMode.STRICT,
            use_ap_drink=True,
            skip_commu=False
        )
        
        # 序列化
        json_data = data.model_dump(mode='json')
        
        # 反序列化
        restored_data = ProduceData.model_validate(json_data)
        
        # 验证数据一致性
        self.assertEqual(restored_data.mode, 'pro')
        self.assertEqual(restored_data.idol, 'test_idol_123')
        self.assertEqual(restored_data.memory_set, 2)
        self.assertEqual(restored_data.support_card_set, 3)
        self.assertTrue(restored_data.auto_set_memory)
        self.assertTrue(restored_data.auto_set_support_card)
        self.assertTrue(restored_data.use_pt_boost)
        self.assertTrue(restored_data.use_note_boost)
        self.assertTrue(restored_data.follow_producer)
        self.assertEqual(restored_data.self_study_lesson, 'vocal')
        self.assertTrue(restored_data.prefer_lesson_ap)
        self.assertEqual(restored_data.actions_order, [ProduceAction.DANCE, ProduceAction.VOCAL])
        self.assertEqual(restored_data.recommend_card_detection_mode, RecommendCardDetectionMode.STRICT)
        self.assertTrue(restored_data.use_ap_drink)
        self.assertFalse(restored_data.skip_commu)


class TestProduceSolution(TestCase):
    """测试 ProduceSolution 类"""

    def test_produce_solution_creation(self):
        """测试创建培育方案"""
        data = ProduceData(mode='pro', idol='test_idol')
        solution = ProduceSolution(
            id='test_id_123',
            name='测试方案',
            description='这是一个测试方案',
            data=data
        )
        
        self.assertEqual(solution.type, 'produce_solution')
        self.assertEqual(solution.id, 'test_id_123')
        self.assertEqual(solution.name, '测试方案')
        self.assertEqual(solution.description, '这是一个测试方案')
        self.assertEqual(solution.data.mode, 'pro')
        self.assertEqual(solution.data.idol, 'test_idol')

    def test_produce_solution_validation(self):
        """测试字段验证"""
        data = ProduceData()
        
        # 测试必需字段
        solution = ProduceSolution(
            id='test_id',
            name='测试方案',
            data=data
        )
        self.assertEqual(solution.id, 'test_id')
        self.assertEqual(solution.name, '测试方案')
        self.assertIsNone(solution.description)

    def test_produce_solution_serialization(self):
        """测试序列化和反序列化"""
        data = ProduceData(mode='master', idol='test_idol_456')
        solution = ProduceSolution(
            id='test_id_456',
            name='高级测试方案',
            description='这是一个高级测试方案',
            data=data
        )
        
        # 序列化
        json_data = solution.model_dump(mode='json')
        
        # 反序列化
        restored_solution = ProduceSolution.model_validate(json_data)
        
        # 验证数据一致性
        self.assertEqual(restored_solution.type, 'produce_solution')
        self.assertEqual(restored_solution.id, 'test_id_456')
        self.assertEqual(restored_solution.name, '高级测试方案')
        self.assertEqual(restored_solution.description, '这是一个高级测试方案')
        self.assertEqual(restored_solution.data.mode, 'master')
        self.assertEqual(restored_solution.data.idol, 'test_idol_456')


class TestProduceSolutionManager(TestCase):
    """测试 ProduceSolutionManager 类"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.original_solutions_dir = ProduceSolutionManager.SOLUTIONS_DIR
        ProduceSolutionManager.SOLUTIONS_DIR = os.path.join(self.temp_dir, "test_solutions") # type: ignore[assignment]
        self.manager = ProduceSolutionManager()

    def tearDown(self):
        """清理测试环境"""
        # 恢复原始目录设置
        ProduceSolutionManager.SOLUTIONS_DIR = self.original_solutions_dir # type: ignore[assignment]
        # 删除临时目录
        shutil.rmtree(self.temp_dir)

    def test_manager_init(self):
        """测试管理器初始化和目录创建"""
        # 验证目录已创建
        self.assertTrue(os.path.exists(self.manager.SOLUTIONS_DIR))
        self.assertTrue(os.path.isdir(self.manager.SOLUTIONS_DIR))

    def test_sanitize_filename(self):
        """测试文件名清理功能"""
        test_cases = [
            ('正常文件名', '正常文件名'),
            ('包含\\斜杠/的:文件*名?', '包含_斜杠_的_文件_名_'),
            ('包含"引号"和<尖括号>', '包含_引号_和_尖括号_'),
            ('包含|管道符', '包含_管道符'),
            ('', ''),
        ]
        
        for input_name, expected_output in test_cases:
            with self.subTest(input_name=input_name):
                result = self.manager._sanitize_filename(input_name)
                self.assertEqual(result, expected_output)

    def test_get_file_path(self):
        """测试根据名称获取文件路径"""
        name = '测试方案'
        expected_path = os.path.join(self.manager.SOLUTIONS_DIR, '测试方案.json')
        result = self.manager._get_file_path(name)
        self.assertEqual(result, expected_path)

        # 测试特殊字符处理
        name_with_special = '测试/方案:名称'
        expected_path_special = os.path.join(self.manager.SOLUTIONS_DIR, '测试_方案_名称.json')
        result_special = self.manager._get_file_path(name_with_special)
        self.assertEqual(result_special, expected_path_special)

    def test_find_file_path_by_id(self):
        """测试根据ID查找文件路径"""
        # 创建测试文件
        test_id = 'test_id_123'
        solution = ProduceSolution(
            id=test_id,
            name='测试方案',
            data=ProduceData()
        )

        # 保存文件
        file_path = self.manager._get_file_path(solution.name)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(solution.model_dump(mode='json'), f, ensure_ascii=False, indent=4)

        # 测试查找
        found_path = self.manager._find_file_path_by_id(test_id)
        self.assertEqual(found_path, file_path)

        # 测试查找不存在的ID
        not_found_path = self.manager._find_file_path_by_id('nonexistent_id')
        self.assertIsNone(not_found_path)

    def test_new_solution(self):
        """测试创建新方案"""
        name = '新测试方案'
        solution = self.manager.new(name)

        self.assertEqual(solution.name, name)
        self.assertEqual(solution.type, 'produce_solution')
        self.assertIsNotNone(solution.id)
        self.assertIsNone(solution.description)
        self.assertIsInstance(solution.data, ProduceData)

        # 验证ID是有效的UUID
        try:
            uuid.UUID(solution.id)
        except ValueError:
            self.fail("Generated ID is not a valid UUID")

    def test_list_solutions_empty(self):
        """测试空目录时列出方案"""
        solutions = self.manager.list()
        self.assertEqual(solutions, [])

    def test_list_solutions_with_files(self):
        """测试有文件时列出方案"""
        # 创建测试方案
        solution1 = ProduceSolution(
            id='id1',
            name='方案1',
            data=ProduceData(mode='regular')
        )
        solution2 = ProduceSolution(
            id='id2',
            name='方案2',
            data=ProduceData(mode='pro')
        )

        # 保存文件
        for solution in [solution1, solution2]:
            file_path = self.manager._get_file_path(solution.name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(solution.model_dump(mode='json'), f, ensure_ascii=False, indent=4)

        # 列出方案
        solutions = self.manager.list()
        self.assertEqual(len(solutions), 2)

        # 验证方案内容（顺序可能不同）
        solution_ids = {s.id for s in solutions}
        self.assertEqual(solution_ids, {'id1', 'id2'})

    def test_list_solutions_with_invalid_files(self):
        """测试包含无效文件时列出方案"""
        # 创建有效方案文件
        valid_solution = ProduceSolution(
            id='valid_id',
            name='有效方案',
            data=ProduceData()
        )
        valid_file_path = self.manager._get_file_path(valid_solution.name)
        with open(valid_file_path, 'w', encoding='utf-8') as f:
            json.dump(valid_solution.model_dump(mode='json'), f, ensure_ascii=False, indent=4)

        # 创建无效JSON文件
        invalid_file_path = os.path.join(self.manager.SOLUTIONS_DIR, '无效文件.json')
        with open(invalid_file_path, 'w', encoding='utf-8') as f:
            f.write('invalid json content')

        # 创建非JSON文件
        non_json_file_path = os.path.join(self.manager.SOLUTIONS_DIR, '非JSON文件.txt')
        with open(non_json_file_path, 'w', encoding='utf-8') as f:
            f.write('not a json file')

        # 列出方案，应该只返回有效的方案
        solutions = self.manager.list()
        self.assertEqual(len(solutions), 1)
        self.assertEqual(solutions[0].id, 'valid_id')

    def test_save_solution(self):
        """测试保存方案"""
        solution = ProduceSolution(
            id='save_test_id',
            name='保存测试方案',
            description='测试保存功能',
            data=ProduceData(mode='master', idol='test_idol')
        )

        # 保存方案
        self.manager.save(solution.id, solution)

        # 验证文件已创建
        expected_file_path = self.manager._get_file_path(solution.name)
        self.assertTrue(os.path.exists(expected_file_path))

        # 验证文件内容
        with open(expected_file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data['id'], 'save_test_id')
        self.assertEqual(saved_data['name'], '保存测试方案')
        self.assertEqual(saved_data['description'], '测试保存功能')
        self.assertEqual(saved_data['data']['mode'], 'master')
        self.assertEqual(saved_data['data']['idol'], 'test_idol')

    def test_save_solution_with_name_change(self):
        """测试保存时名称变更的处理"""
        solution_id = 'name_change_test_id'

        # 创建初始方案
        original_solution = ProduceSolution(
            id=solution_id,
            name='原始名称',
            data=ProduceData()
        )
        self.manager.save(solution_id, original_solution)
        original_file_path = self.manager._get_file_path('原始名称')
        self.assertTrue(os.path.exists(original_file_path))

        # 修改名称并保存
        updated_solution = ProduceSolution(
            id=solution_id,
            name='新名称',
            data=ProduceData()
        )
        self.manager.save(solution_id, updated_solution)

        # 验证旧文件已删除，新文件已创建
        self.assertFalse(os.path.exists(original_file_path))
        new_file_path = self.manager._get_file_path('新名称')
        self.assertTrue(os.path.exists(new_file_path))

    def test_read_solution(self):
        """测试读取方案"""
        # 创建并保存方案
        solution = ProduceSolution(
            id='read_test_id',
            name='读取测试方案',
            description='测试读取功能',
            data=ProduceData(mode='pro', memory_set=5)
        )
        self.manager.save(solution.id, solution)

        # 读取方案
        read_solution = self.manager.read(solution.id)

        # 验证读取的数据
        self.assertEqual(read_solution.id, 'read_test_id')
        self.assertEqual(read_solution.name, '读取测试方案')
        self.assertEqual(read_solution.description, '测试读取功能')
        self.assertEqual(read_solution.data.mode, 'pro')
        self.assertEqual(read_solution.data.memory_set, 5)

    def test_read_nonexistent_solution(self):
        """测试读取不存在的方案"""
        with self.assertRaises(ProduceSolutionNotFoundError) as context:
            self.manager.read('nonexistent_id')

        self.assertIn("Solution with id 'nonexistent_id' not found", str(context.exception))

    def test_delete_solution(self):
        """测试删除方案"""
        # 创建并保存方案
        solution = ProduceSolution(
            id='delete_test_id',
            name='删除测试方案',
            data=ProduceData()
        )
        self.manager.save(solution.id, solution)

        # 验证文件存在
        file_path = self.manager._get_file_path(solution.name)
        self.assertTrue(os.path.exists(file_path))

        # 删除方案
        self.manager.delete(solution.id)

        # 验证文件已删除
        self.assertFalse(os.path.exists(file_path))

    def test_delete_nonexistent_solution(self):
        """测试删除不存在的方案"""
        # 删除不存在的方案不应该抛出异常
        try:
            self.manager.delete('nonexistent_id')
        except Exception as e:
            self.fail(f"Deleting nonexistent solution should not raise exception: {e}")

    def test_duplicate_solution(self):
        """测试复制方案"""
        # 创建原始方案
        original_solution = ProduceSolution(
            id='original_id',
            name='原始方案',
            description='原始描述',
            data=ProduceData(mode='master', idol='test_idol', memory_set=3)
        )
        self.manager.save(original_solution.id, original_solution)

        # 复制方案
        duplicated_solution = self.manager.duplicate(original_solution.id)

        # 验证复制的方案
        self.assertNotEqual(duplicated_solution.id, original_solution.id)
        self.assertEqual(duplicated_solution.name, '原始方案 - 副本')
        self.assertEqual(duplicated_solution.description, '原始描述')
        self.assertEqual(duplicated_solution.type, 'produce_solution')

        # 验证数据深拷贝
        self.assertEqual(duplicated_solution.data.mode, 'master')
        self.assertEqual(duplicated_solution.data.idol, 'test_idol')
        self.assertEqual(duplicated_solution.data.memory_set, 3)

        # 验证是深拷贝而不是浅拷贝
        self.assertIsNot(duplicated_solution.data, original_solution.data)

        # 验证新ID是有效的UUID
        try:
            uuid.UUID(duplicated_solution.id)
        except ValueError:
            self.fail("Duplicated solution ID is not a valid UUID")

    def test_duplicate_nonexistent_solution(self):
        """测试复制不存在的方案"""
        with self.assertRaises(ProduceSolutionNotFoundError):
            self.manager.duplicate('nonexistent_id')

    def test_corrupted_json_handling(self):
        """测试处理损坏的JSON文件"""
        # 创建损坏的JSON文件
        corrupted_file_path = os.path.join(self.manager.SOLUTIONS_DIR, '损坏文件.json')
        with open(corrupted_file_path, 'w', encoding='utf-8') as f:
            f.write('{"id": "corrupted_id", "name": "corrupted", invalid json}')

        # list() 方法应该跳过损坏的文件
        solutions = self.manager.list()
        self.assertEqual(len(solutions), 0)

        # _find_file_path_by_id 应该跳过损坏的文件
        found_path = self.manager._find_file_path_by_id('corrupted_id')
        self.assertIsNone(found_path)

    def test_special_characters_in_names(self):
        """测试名称中的特殊字符处理"""
        special_names = [
            '包含/斜杠的名称',
            '包含:冒号的名称',
            '包含*星号的名称',
            '包含?问号的名称',
            '包含"引号的名称',
            '包含<尖括号>的名称',
            '包含|管道符的名称',
        ]

        for name in special_names:
            with self.subTest(name=name):
                # 创建方案
                solution = ProduceSolution(
                    id=f'special_id_{hash(name)}',
                    name=name,
                    data=ProduceData()
                )

                # 保存方案
                self.manager.save(solution.id, solution)

                # 验证能够读取
                read_solution = self.manager.read(solution.id)
                self.assertEqual(read_solution.name, name)

                # 验证能够列出
                solutions = self.manager.list()
                names = [s.name for s in solutions]
                self.assertIn(name, names)

    def test_full_workflow(self):
        """测试完整的工作流程（创建→保存→读取→修改→删除）"""
        # 1. 创建新方案
        solution = self.manager.new('工作流程测试')
        original_id = solution.id

        # 2. 修改方案数据
        solution.description = '完整工作流程测试'
        solution.data.mode = 'pro'
        solution.data.idol = 'workflow_test_idol'

        # 3. 保存方案
        self.manager.save(solution.id, solution)

        # 4. 读取方案
        read_solution = self.manager.read(solution.id)
        self.assertEqual(read_solution.id, original_id)
        self.assertEqual(read_solution.name, '工作流程测试')
        self.assertEqual(read_solution.description, '完整工作流程测试')
        self.assertEqual(read_solution.data.mode, 'pro')
        self.assertEqual(read_solution.data.idol, 'workflow_test_idol')

        # 5. 修改方案名称
        read_solution.name = '修改后的名称'
        self.manager.save(read_solution.id, read_solution)

        # 6. 验证修改
        modified_solution = self.manager.read(read_solution.id)
        self.assertEqual(modified_solution.name, '修改后的名称')

        # 7. 复制方案
        duplicated = self.manager.duplicate(modified_solution.id)
        self.assertNotEqual(duplicated.id, modified_solution.id)
        self.assertEqual(duplicated.name, '修改后的名称 - 副本')

        # 8. 列出所有方案
        all_solutions = self.manager.list()
        self.assertEqual(len(all_solutions), 1)  # 只有原始方案，复制的方案还没保存

        # 9. 保存复制的方案
        self.manager.save(duplicated.id, duplicated)
        all_solutions = self.manager.list()
        self.assertEqual(len(all_solutions), 2)

        # 10. 删除原始方案
        self.manager.delete(modified_solution.id)
        remaining_solutions = self.manager.list()
        self.assertEqual(len(remaining_solutions), 1)
        self.assertEqual(remaining_solutions[0].id, duplicated.id)

        # 11. 删除复制的方案
        self.manager.delete(duplicated.id)
        final_solutions = self.manager.list()
        self.assertEqual(len(final_solutions), 0)

    def test_concurrent_operations(self):
        """测试并发操作的安全性"""
        # 这个测试主要验证基本的文件操作不会相互干扰
        solutions = []

        # 创建多个方案
        for i in range(5):
            solution = self.manager.new(f'并发测试方案{i}')
            solution.data.mode = 'pro' if i % 2 == 0 else 'regular'
            solutions.append(solution)

        # 同时保存所有方案
        for solution in solutions:
            self.manager.save(solution.id, solution)

        # 验证所有方案都已保存
        saved_solutions = self.manager.list()
        self.assertEqual(len(saved_solutions), 5)

        # 验证每个方案的数据完整性
        for original in solutions:
            read_solution = self.manager.read(original.id)
            self.assertEqual(read_solution.name, original.name)
            self.assertEqual(read_solution.data.mode, original.data.mode)

        # 同时删除所有方案
        for solution in solutions:
            self.manager.delete(solution.id)

        # 验证所有方案都已删除
        remaining_solutions = self.manager.list()
        self.assertEqual(len(remaining_solutions), 0)
