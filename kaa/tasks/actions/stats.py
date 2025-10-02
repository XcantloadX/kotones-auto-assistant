import logging
from typing import NamedTuple
from datetime import timedelta
from kaa.tasks import R
from kotonebot import action, ocr, regex

logger = logging.getLogger(__name__)

class AP(NamedTuple):
    current: int
    total: int
    next_refresh: timedelta

    def __repr__(self):
        return f'AP({self.current}/{self.total} {self.next_refresh})'

@action('获取当前 AP')
def ap() -> AP | None:
    texts = ocr.ocr(rect=R.Daily.BoxHomeAP)
    logger.info(f'BoxHomeAP ocr result: {texts}')
    # 当前 AP 和总 AP
    ap = texts.where(regex(r'\d+/\d+')).first()
    if not ap:
        logger.warning('AP not found.')
        return None
    current, total = ap.numbers()
    # 下一次刷新时间
    next_refresh = texts.where(regex(r'\d+:\d+')).first()
    if not next_refresh:
        logger.warning('Next refresh time not found.')
        return None
    next_refresh = timedelta(minutes=next_refresh.numbers()[0], seconds=next_refresh.numbers()[1])
    return AP(current=current, total=total, next_refresh=next_refresh)

@action('获取当前宝石')
def jewel() -> int | None:
    jewel = ocr.find(regex(r'[\d,]+'), rect=R.Daily.BoxHomeJewel)
    logger.info(f'BoxHomeJewel find result: {jewel}')
    if not jewel:
        logger.warning('Jewel not found.')
        return None
    return int(jewel.text.replace(',', '').replace('+', ''))


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    print(ap())
    print(jewel())
