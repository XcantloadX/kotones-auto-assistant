from time import sleep

from util import *
from kotonebot.tasks.actions.scenes import (
    goto_home,
    goto_shop,
    at_home,
    at_daily_shop,
)
img_assign = 'tests/images/scenes/assign.png'
img_commu = 'tests/images/scenes/commu.png'
img_contest = 'tests/images/scenes/contest.png'
img_home = 'tests/images/scenes/home.png'
img_mission = 'tests/images/scenes/mission.png'
img_present = 'tests/images/scenes/present.png'
img_produce1 = 'tests/images/scenes/produce1.png'
img_produce2 = 'tests/images/scenes/produce2.png'
img_shop = 'tests/images/scenes/shop.png'


class TestActionScenes(BaseTestCase):
    def test_at_home(self):
        yes = [img_home]
        no = [img_assign, img_commu, img_contest, img_mission, img_present, img_produce1, img_produce2, img_shop]
        for image in yes:
            self.device.inject_image(image)
            self.assertTrue(at_home(), 'at_home should find the home button')
        for image in no:
            self.device.inject_image(image)
            self.assertFalse(at_home(), 'at_home should not find the home button')

    def test_goto_home(self):
        yes = [
            img_assign,
            img_commu,
            img_mission,
            img_present,
            img_produce1,
            img_produce2,
            img_shop
        ]
        no = [
            img_contest,
            img_home,
        ]
        for image in yes:
            self.device.inject_image(image)
            goto_home()
            self.assertPointInRect(self.device.last_click, (53, 1183), (121, 1245))
        for image in no:
            self.device.inject_image(image)
            has_exception = False
            try:
                goto_home()
            except Exception as e:
                has_exception = True
            self.assertTrue(has_exception, 'goto_home should not find the home button')

