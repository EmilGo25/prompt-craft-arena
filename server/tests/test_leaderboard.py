from server.leaderboard import LeaderboardStore


def test_average_per_round_ranking(tmp_path):
    store = LeaderboardStore(str(tmp_path / "lb.json"))
    # Ann: 240 over 3 rounds (avg 80). Bo: 180 over 3 rounds (avg 60).
    store.record_game([("Ann", 240), ("Bo", 180)], rounds_played=3)
    top = store.top()
    assert [e.name for e in top] == ["Ann", "Bo"]
    assert top[0].avg == 80 and top[1].avg == 60
    assert top[0].games == 1


def test_average_accumulates_weighted_by_rounds(tmp_path):
    store = LeaderboardStore(str(tmp_path / "lb.json"))
    store.record_game([("Ann", 240)], rounds_played=3)  # 240/3
    store.record_game([("Ann", 40)], rounds_played=2)   # +40/2
    # avg = (240+40) / (3+2) = 280/5 = 56
    e = store.top()[0]
    assert e.avg == 56
    assert e.games == 2
    assert e.best == 80  # best single-game per-round avg (240/3)


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "lb.json")
    LeaderboardStore(path).record_game([("Ann", 90)], rounds_played=1)
    reopened = LeaderboardStore(path)
    assert reopened.top()[0].name == "Ann"
    assert reopened.top()[0].avg == 90


def test_name_case_insensitive_merge(tmp_path):
    store = LeaderboardStore(str(tmp_path / "lb.json"))
    store.record_game([("Ann", 80)], rounds_played=1)
    store.record_game([("ann", 100)], rounds_played=1)
    top = store.top()
    assert len(top) == 1
    assert top[0].avg == 90  # (80+100)/2
