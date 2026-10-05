from features import windowed_features


def test_empty_sequence_is_all_zeros():
    assert windowed_features([]) == {
        "max_window_match_rate": 0.0, "min_window_avg_cp_loss": 0.0,
        "perfect_move_frac": 0.0, "longest_perfect_streak": 0}


def test_all_perfect_moves():
    f = windowed_features([0] * 20)
    assert f["max_window_match_rate"] == 100.0
    assert f["perfect_move_frac"] == 1.0
    assert f["longest_perfect_streak"] == 20


def test_burst_of_engine_moves_shows_in_window_but_not_whole_game():
    # 30 sloppy moves with a 10-move perfect burst in the middle
    seq = [80] * 10 + [0] * 10 + [80] * 10
    f = windowed_features(seq)
    assert f["max_window_match_rate"] == 100.0
    assert f["longest_perfect_streak"] == 10
    assert round(f["perfect_move_frac"], 2) == 0.33


def test_game_shorter_than_one_window_still_scores():
    f = windowed_features([0, 0, 100])
    assert f["max_window_match_rate"] == 66.7


def test_threshold_boundary_counts_as_perfect():
    assert windowed_features([5, 6])["longest_perfect_streak"] == 1
