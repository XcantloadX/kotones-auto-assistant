import unittest
from threading import Event, Thread
import time

from kotonebot.backend.context import (
    interruptible, interruptible_class, vars, sleep,
    image, ocr, color,
)
from util import BaseTestCase


class TestContextInterruptible(BaseTestCase):
    def setUp(self):
        # 每个测试前重置中断状态
        vars.flow.clear_interrupt()

    def test_interruptible(self):
        # 测试正常函数调用
        @interruptible
        def test_func():
            return "success"
        
        self.assertEqual(test_func(), "success")

        # 测试中断情况
        vars.flow.request_interrupt()
        with self.assertRaises(KeyboardInterrupt):
            test_func()

    def test_interruptible_with_args(self):
        # 测试带参数的函数
        @interruptible
        def test_func_with_args(x, y=2):
            return x + y
        
        self.assertEqual(test_func_with_args(1), 3)
        self.assertEqual(test_func_with_args(1, y=3), 4)

        # 测试中断情况
        vars.flow.request_interrupt()
        with self.assertRaises(KeyboardInterrupt):
            test_func_with_args(1)

    def test_interruptible_class(self):
        # 测试类装饰器
        @interruptible_class
        class TestClass:
            def method1(self):
                return "method1"
            
            def method2(self, x):
                return f"method2: {x}"
        
        obj = TestClass()
        
        # 测试正常调用
        self.assertEqual(obj.method1(), "method1")
        self.assertEqual(obj.method2("test"), "method2: test")

        # 测试中断情况
        vars.flow.request_interrupt()
        with self.assertRaises(KeyboardInterrupt):
            obj.method1()
        with self.assertRaises(KeyboardInterrupt):
            obj.method2("test")

    def test_interruptible_multithreading(self):
        # 用于存储线程执行结果
        results = []
        exceptions = []

        @interruptible
        def long_running_task(sleep_time):
            sleep(sleep_time)
            results.append("completed")
            return "success"

        def thread_func():
            try:
                long_running_task(2)
            except KeyboardInterrupt as e:
                exceptions.append(e)

        # 创建并启动3个线程
        threads = [Thread(target=thread_func) for _ in range(3)]
        for t in threads:
            t.start()

        # 等待一小段时间后设置中断标志
        time.sleep(0.5)
        vars.flow.request_interrupt()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证结果
        self.assertTrue(len(exceptions) == 3)

    def test_sleep(self):
        vars.flow.request_interrupt()
        with self.assertRaises(KeyboardInterrupt):
            sleep(2)

    def test_context_ocr_interruptible(self):
        # 测试 ContextOcr 的可中断性
        vars.flow.request_interrupt()
        with self.assertRaises(KeyboardInterrupt):
            ocr.ocr()
        with self.assertRaises(KeyboardInterrupt):
            ocr.find("test")
        with self.assertRaises(KeyboardInterrupt):
            ocr.expect("test")
        with self.assertRaises(KeyboardInterrupt):
            ocr.expect_wait("test")

    def test_context_image_interruptible(self):
        # 测试 ContextImage 的可中断性
        vars.flow.request_interrupt()
        with self.assertRaises(KeyboardInterrupt):
            image.find("test.png")
        with self.assertRaises(KeyboardInterrupt):
            image.expect("test.png")
        with self.assertRaises(KeyboardInterrupt):
            image.find_all("test.png")
        with self.assertRaises(KeyboardInterrupt):
            image.find_multi(["test.png"])
        with self.assertRaises(KeyboardInterrupt):
            image.wait_for("test.png")
        with self.assertRaises(KeyboardInterrupt):
            image.wait_for_any(["test.png"])

    def test_context_color_interruptible(self):
        # 测试 ContextColor 的可中断性
        vars.flow.request_interrupt()
        with self.assertRaises(KeyboardInterrupt):
            color.find((255, 255, 255))

    
