from server.rooms.state import (
    GameState,
    Phase,
    Player,
    RoundResult,
    Submission,
    round_winner,
    standings,
)


def make_state() -> GameState:
    state = GameState(total_rounds=3, round_seconds=30)
    state.add_player(Player(id="a", name="Ann"))
    state.add_player(Player(id="b", name="Bo"))
    return state


def test_first_player_is_host():
    state = make_state()
    assert state.players["a"].is_host is True
    assert state.players["b"].is_host is False
    assert state.host_id() == "a"


def test_all_connected_submitted():
    state = make_state()
    state.phase = Phase.PROMPTING
    state.current_round = RoundResult(target_image_id="t")
    assert state.all_connected_submitted() is False

    state.current_round.submissions["a"] = Submission("a", "cat")
    assert state.all_connected_submitted() is False
    state.current_round.submissions["b"] = Submission("b", "dog")
    assert state.all_connected_submitted() is True


def test_disconnected_player_excluded_from_submission_check():
    state = make_state()
    state.phase = Phase.PROMPTING
    state.current_round = RoundResult(target_image_id="t")
    state.players["b"].connected = False
    state.current_round.submissions["a"] = Submission("a", "cat")
    # Only Ann is connected and she submitted -> round can resolve.
    assert state.all_connected_submitted() is True


def test_apply_scores_accumulates():
    state = make_state()
    state.current_round = RoundResult(target_image_id="t")
    state.apply_scores({"a": 80, "b": 40})
    state.current_round = RoundResult(target_image_id="t2")
    state.apply_scores({"a": 10, "b": 95})
    assert state.players["a"].score == 90
    assert state.players["b"].score == 135
    ranked = standings(state)
    assert [p.id for p in ranked] == ["b", "a"]


def test_round_winner():
    rnd = RoundResult(target_image_id="t", scores={"a": 30, "b": 70})
    assert round_winner(rnd) == "b"
    assert round_winner(RoundResult(target_image_id="t")) is None
