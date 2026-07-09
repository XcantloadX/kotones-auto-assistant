from pathlib import Path

import pytest

from kaa.db._util import clear_db_caches
from kaa.db.drink import Drink
from kaa.db.idol_card import IdolCard
from kaa.db.school_event import SchoolEvent
from kaa.db.skill_card import SkillCard
from kaa.game_data.paths import game_db_path

pytestmark = pytest.mark.skipif(
    not game_db_path().exists(),
    reason='game.db not available',
)


def test_drink_from_asset_id():
    drink = Drink.from_asset_id('img_general_pdrink_1-001')
    assert drink is not None
    assert drink.name


def test_drink_all_cached():
    drinks = Drink.all()
    assert len(drinks) > 0
    assert drinks is Drink.all()


def test_idol_card_all():
    cards = IdolCard.all()
    assert len(cards) > 0


def test_skill_card_from_asset_id():
    card = SkillCard.from_asset_id('img_general_skillcard_ido-3_102')
    assert card is not None
    assert card.name


def test_school_event_load_all():
    events = SchoolEvent.load_all()
    assert len(events) > 1000


def test_school_event_get_matches_load_all():
    events = SchoolEvent.load_all()
    sample = events[0]
    assert SchoolEvent.get(sample.event_id) == sample


def test_clear_db_caches():
    SchoolEvent.load_all()
    clear_db_caches()
    assert SchoolEvent.load_all()