from app.engine.normalize import masked_tokens, normalize_message


def test_masks_numbers_ids_and_durations_consistently():
    a = normalize_message("connection pool exhausted for db-7 after 1423ms")
    b = normalize_message("connection pool exhausted for db-3 after 88ms")
    # Different variable values must collapse to the same template.
    assert a == b
    assert "<DUR>" in a


def test_masks_typed_tokens():
    msg = "user 550e8400-e29b-41d4-a716-446655440000 from 10.0.0.5:8080 hit /api/v1/pay 500 42%"
    norm = normalize_message(msg)
    assert "<UUID>" in norm
    assert "<IP>" in norm
    assert "<PATH>" in norm
    assert "<PCT>" in norm


def test_specific_masks_beat_generic_number():
    # An IP should not be shredded into <NUM>.<NUM>...
    norm = normalize_message("request from 192.168.1.20 failed")
    assert norm == "request from <IP> failed"


def test_masked_tokens_returns_token_list():
    tokens = masked_tokens("charge 42 authorized in 120ms")
    assert tokens == ["charge", "<NUM>", "authorized", "in", "<DUR>"]
