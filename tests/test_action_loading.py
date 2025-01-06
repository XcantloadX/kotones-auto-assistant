import unittest

from kotonebot.backend.context import _c
from kotonebot import device, debug
from util import *

debug.save_images = True
debug.save_images_dir = "tests/output_images"

class TestActionLoading(unittest.TestCase):
    loadings = [f'tests/images/ui/loading_{i}.png' for i in range(1, 10)]
    not_loadings = [f'tests/images/ui/not_loading_{i}.png' for i in range(1, 5)]


    @classmethod
    def setUpClass(cls):
        cls.d = MockDevice('')
        _c.inject_device(cls.d)

    def test_loading(self):
        for loading in self.loadings:
            self.d.screenshot_path = loading
            from kotonebot.tasks.actions import loading
            self.assertTrue(loading.loading())

    def test_not_loading(self):
        for not_loading in self.not_loadings:
            self.d.screenshot_path = not_loading
            from kotonebot.tasks.actions import loading
            self.assertFalse(loading.loading())
