import logging

from kaa.db._util import collect_ids, load_by_ids, log_missing_ids, parse_id_list, parse_json_list


def test_parse_id_list():
    assert parse_id_list('["a", "b"]') == ['a', 'b']
    assert parse_id_list(None) == []
    assert parse_id_list('invalid') == []


def test_parse_json_list():
    assert parse_json_list('[1, 2]') == [1, 2]
    assert parse_json_list('{}') == []


def test_collect_ids():
    rows = [
        {'produceStepEventSuggestionIds': '["s1", "s2"]'},
        {'produceStepEventSuggestionIds': '["s2", "s3"]'},
    ]
    assert collect_ids(rows, 'produceStepEventSuggestionIds') == {'s1', 's2', 's3'}


def test_load_by_ids_empty():
    assert load_by_ids('ProduceEffect', []) == []


def test_parse_json_list_logs_invalid_json(caplog):
    caplog.set_level(logging.ERROR)
    assert parse_json_list('invalid', context='test') == []
    assert 'invalid JSON' in caplog.text


def test_log_missing_ids(caplog):
    caplog.set_level(logging.ERROR)
    log_missing_ids('test context', ['a', 'b', 'c'], {'a': 1})
    assert 'test context' in caplog.text
    assert 'missing id' in caplog.text