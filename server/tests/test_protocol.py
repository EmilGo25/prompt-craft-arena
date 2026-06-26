import pytest
from pydantic import ValidationError

from server.realtime import protocol as p


def test_parse_submit_prompt():
    msg = p.parse_client_message('{"type":"submit_prompt","prompt":"a sunset"}')
    assert isinstance(msg, p.SubmitPrompt)
    assert msg.prompt == "a sunset"


def test_parse_start_game():
    assert isinstance(p.parse_client_message('{"type":"start_game"}'), p.StartGame)


def test_unknown_type_rejected():
    with pytest.raises(ValidationError):
        p.parse_client_message('{"type":"nonsense"}')


def test_empty_prompt_rejected():
    with pytest.raises(ValidationError):
        p.parse_client_message('{"type":"submit_prompt","prompt":""}')


def test_server_message_round_trips():
    msg = p.RoundReveal(
        round_num=1,
        target_image_id="t1",
        results=[
            p.ResultView(
                player_id="a", player_name="Ann", prompt="cat",
                image_id="i1", score=80, rationale="close",
            )
        ],
        winner_id="a",
        standings=[p.PlayerView(id="a", name="Ann", score=80, connected=True, is_host=True)],
    )
    data = msg.model_dump_json()
    again = p.RoundReveal.model_validate_json(data)
    assert again.results[0].score == 80
    assert again.winner_id == "a"
