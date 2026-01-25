from typing import Callable
from typing_extensions import override

import cv2
import numpy as np
from cv2.typing import MatLike

from kaa.config import conf
from kaa.tasks.produce.cards import CardDetectResult, calc_card_position, SKIP_CARD_BUTTON, skill_card_count
from kaa.util.trace import trace
from kotonebot import logging, use_screenshot, device
from kotonebot.primitives import Rect

from .strategy import AbstractBattleStrategy

logger = logging.getLogger(__name__)


class BandaiStrategy(AbstractBattleStrategy):
	def __init__(self, threshold_predicate: Callable[[int, CardDetectResult], bool]):
		self._threshold_predicate = threshold_predicate

	@override
	def on_action(self, ctx):
		img = device.screenshot()
		card_count = skill_card_count(img)
		if card_count <= 0:
			logger.info("No cards detected for recommended-card strategy.")
			return False
		result = detect_recommended_card(card_count, self._threshold_predicate, img=img)
		if result is None:
			logger.info("No recommended card detected.")
			return False
		device.double_click(result)
		return True


def detect_recommended_card(
		card_count: int,
		threshold_predicate: Callable[[int, CardDetectResult], bool],
		*,
		img: MatLike | None = None,
	):
	"""
	识别推荐卡片

	前置条件：练习或考试中\n
	结束状态：-

	:param card_count: 卡片数量(2-4)
	:param threshold_predicate: 阈值判断函数
	:return: 执行结果。若返回 None，表示未识别到推荐卡片。
	"""
	YELLOW_LOWER = np.array([20, 100, 100])
	YELLOW_UPPER = np.array([30, 255, 255])
	GLOW_EXTENSION = 15

	cards = calc_card_position(card_count)
	cards.append(SKIP_CARD_BUTTON)

	img = use_screenshot(img)
	original_image = img.copy()
	results: list[CardDetectResult] = []
	for x, y, w, h, return_value in cards:
		outer = (max(0, x - GLOW_EXTENSION), max(0, y - GLOW_EXTENSION))
		# 裁剪出检测区域
		glow_area = img[outer[1]:y + h + GLOW_EXTENSION, outer[0]:x + w + GLOW_EXTENSION]
		area_h = glow_area.shape[0]
		area_w = glow_area.shape[1]
		glow_area[GLOW_EXTENSION:area_h-GLOW_EXTENSION, GLOW_EXTENSION:area_w-GLOW_EXTENSION] = 0

		# 过滤出目标黄色
		glow_area = cv2.cvtColor(glow_area, cv2.COLOR_BGR2HSV)
		yellow_mask = cv2.inRange(glow_area, YELLOW_LOWER, YELLOW_UPPER)

		# 分割出每一边
		left_border = yellow_mask[:, 0:GLOW_EXTENSION]
		right_border = yellow_mask[:, area_w-GLOW_EXTENSION:area_w]
		top_border = yellow_mask[0:GLOW_EXTENSION, :]
		bottom_border = yellow_mask[area_h-GLOW_EXTENSION:area_h, :]
		y_border_pixels = area_h * GLOW_EXTENSION
		x_border_pixels = area_w * GLOW_EXTENSION

		# 计算每一边的分数
		left_score = np.count_nonzero(left_border) / y_border_pixels
		right_score = np.count_nonzero(right_border) / y_border_pixels
		top_score = np.count_nonzero(top_border) / x_border_pixels
		bottom_score = np.count_nonzero(bottom_border) / x_border_pixels

		result = (left_score + right_score + top_score + bottom_score) / 4
		results.append(CardDetectResult(
			return_value,
			result,
			left_score,
			right_score,
			top_score,
			bottom_score,
			Rect(x, y, w, h)
		))
		img = original_image.copy()
	#     cv2.imshow(f"card detect {return_value}", cv2.cvtColor(glow_area, cv2.COLOR_HSV2BGR))
	#     cv2.namedWindow(f"card detect {return_value}", cv2.WINDOW_NORMAL)
	#     cv2.moveWindow(f"card detect {return_value}", 100 + (return_value % 3) * 300, 100 + (return_value // 3) * 300)
	# cv2.waitKey(1)
	filtered_results = list(filter(lambda result: threshold_predicate(card_count, result), results))
	if not filtered_results:
		max_result = max(results, key=lambda x: x.score)
		logger.verbose("Max card detect result (discarded): value=%d score=%.4f borders=(%.4f, %.4f, %.4f, %.4f)",
			max_result.type,
			max_result.score,
			max_result.left_score,
			max_result.right_score,
			max_result.top_score,
			max_result.bottom_score
		)
		return None
	filtered_results.sort(key=lambda x: x.score, reverse=True)
	logger.debug("Max card detect result: value=%d score=%.4f borders=(%.4f, %.4f, %.4f, %.4f)",
		filtered_results[0].type,
		filtered_results[0].score,
		filtered_results[0].left_score,
		filtered_results[0].right_score,
		filtered_results[0].top_score,
		filtered_results[0].bottom_score
	)
	# 跟踪检测结果
	if conf().trace.recommend_card_detection:
		x, y, w, h = filtered_results[0].rect.xywh
		cv2.rectangle(original_image, (x, y), (x+w, y+h), (0, 0, 255), 3)
		trace('rec-card', original_image, {
			'card_count': card_count,
			'type': filtered_results[0].type,
			'score': filtered_results[0].score,
			'borders': (
				filtered_results[0].left_score,
				filtered_results[0].right_score,
				filtered_results[0].top_score,
				filtered_results[0].bottom_score
			)
		})
	return filtered_results[0]
