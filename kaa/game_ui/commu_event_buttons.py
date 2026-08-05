import random
import uuid
from dataclasses import dataclass

import cv2
from cv2.typing import MatLike

from kaa.config import conf
from kaa.util.trace import trace_named
from kotonebot.primitives import Rect
from kotonebot.backend.core import HintBox
from kotonebot import device, ocr, sleep

DEBUG = False


@dataclass
class EventButton:
    rect: Rect
    selected: bool
    description: str
    title: str

@dataclass
class Region:
    rect: Rect
    seems_button: bool
    white_ratio: float
    is_selected: bool

# 参考图片：
# [screenshots/produce/action_study3.png]
# TODO: CommuEventButtonUI 需要能够识别不可用的按钮
class CommuEventButtonUI:
    """
    此类用于识别培育中交流中出现的事件/效果里的按钮。

    例如外出（おでかけ）、冲刺周课程选择这两个页面的选择按钮。
    """
    def __init__(self, rect: HintBox | None = None):
        """
        :param rect: 识别范围
        """
        from ..tasks import R
        self.rect = rect or R.InProduce.BoxCommuEventButtonsArea

    def _detect_regions(self, img: MatLike) -> list[Region]:
        """
        识别流程：
        1. 截图并裁剪到 ROI
        2. 二值化 (190 threshold)
        3. Canny 边缘检测 (200, 250)
        4. 形态学闭运算 + 膨胀 (7x7 kernel)
        5. 轮廓查找，按尺寸过滤 (350 < w < 660, h > 60)
        6. 判断类型（按钮/描述）和选中状态
        """
        roi = self.rect.xyxy
        cropped = img[roi[1]:roi[3], roi[0]:roi[2]]

        binary = cv2.threshold(cropped, 190, 255, cv2.THRESH_BINARY)[1]
        edges = cv2.Canny(binary, 200, 250)
        # 形态学
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        edges = cv2.dilate(edges, kernel, iterations=1)

        if DEBUG:
            cv2.imshow('Edges', cv2.resize(edges, None, fx=0.75, fy=0.75))
            cv2.imshow('Binary', cv2.resize(binary, None, fx=0.75, fy=0.75))

        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        results: list[Region] = []
        # 第一遍获取信息
        for contour in contours:
            # 计算轮廓的边界框
            x, y, w, h = cv2.boundingRect(contour)
            if not (350 < w < 660 and h > 60):
                continue

            is_button = 60 < h < 100

            contour_slice = cropped[y:y+h, x:x+w]
            contour_slice = cv2.cvtColor(contour_slice, cv2.COLOR_BGR2GRAY)
            contour_slice = cv2.threshold(contour_slice, 190, 255, cv2.THRESH_BINARY)[1]
            ratio: float = (contour_slice == 255).mean()
            is_selected = is_button and ratio < 0.5

            results.append(Region(Rect(roi[0] + x, roi[1] + y, w, h), is_button, ratio, is_selected))

        # 第二遍：如果有 result 为选中状态，那么第一个结果视为描述
        results.sort(key=lambda r: r.rect.y1)  # 按 y 坐标排序
        has_any_selected = any(r.is_selected for r in results)
        if has_any_selected and results:
            results[0].seems_button = False
            results[0].is_selected = False

        if DEBUG:
            canvas = cropped.copy()
            for r in results:
                # draw pos info
                x, y, w, h = r.rect.xywh
                lx, ly = x - roi[0], y - roi[1]
                label = 'Button' if r.seems_button else 'Description'
                color = (0, 0, 255) if r.is_selected else (0, 255, 0)
                cv2.putText(canvas, f"{label} ({x}, {y}, {w}, {h})", (lx, ly - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.rectangle(canvas, (lx, ly), (lx + w, ly + h), color, 2)
            cv2.putText(canvas, f"Count: {len(results)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Contours', cv2.resize(canvas, None, fx=0.75, fy=0.75))
            cv2.waitKey(1)

        return results

    def _trace_all(self, img: MatLike, rects: list[Rect]) -> None:
        if not conf().trace.commu_event_buttons:
            return
        if rects:
            should_trace = True
        else:
            should_trace = random.random() < 0.2
        if not should_trace:
            return
        trace_id = uuid.uuid4().hex
        n = len(rects)
        images = {f'rect_{n}_1_{trace_id}': img}
        if rects:
            annotated_img = img.copy()
            for rect in rects:
                x, y, w, h = rect.xywh
                cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (0, 0, 255), 3)
            images[f'rect_{n}_2_{trace_id}'] = annotated_img
        trace_named('commu-event-buttons', images, {
            'rect_count': n,
            'rects': [rect.xywh for rect in rects],
        })

    def selected(self, description: bool = True, title: bool = False) -> EventButton | None:
        img = device.screenshot()
        regions = self._detect_regions(img)
        for r in regions:
            if r.is_selected:
                desc_text = self.description() if description else ''
                title_text = ocr.ocr(rect=r.rect).squash().text if title else ''
                return EventButton(r.rect, True, desc_text, title_text)
        return None

    def all(self, description: bool = True, title: bool = False) -> list[EventButton]:
        """
        识别所有按钮的位置以及选中后的描述文本

        前置条件：当前显示了交流事件按钮\n
        结束状态：-

        :param description: 是否识别描述文本。
        :param title: 是否识别标题。
        """
        img = device.screenshot()
        regions = self._detect_regions(img)
        buttons = [r for r in regions if r.seems_button]
        self._trace_all(img, [r.rect for r in buttons])
        if not buttons:
            return []

        result: list[EventButton] = []
        for btn in buttons:
            desc_text = ''
            title_text = ''
            if title:
                title_text = ocr.ocr(rect=btn.rect).squash().text
            if description:
                if btn.is_selected:
                    desc_text = self.description()
                else:
                    device.click(btn.rect)
                    sleep(0.15)
                    device.screenshot()
                    desc_text = self.description()
            result.append(EventButton(btn.rect, btn.is_selected, desc_text, title_text))

        result.sort(key=lambda x: x.rect.y1)
        return result

    def description(self) -> str:
        """
        识别当前选中按钮的描述文本

        前置条件：有选中按钮\n
        结束状态：-
        """
        img = device.screenshot()
        regions = self._detect_regions(img)
        if not regions:
            return ''
        ocr_result = ocr.raw().ocr(img, rect=regions[0].rect)
        return ocr_result.squash().text
