"""
features.py

Turns a raw per-move centipawn-loss sequence into features that can catch
INTERMITTENT cheating, not just whole-game averages. This exists because
whole-game averages (top1_match_rate, avg_centipawn_loss) dilute a burst of
engine-perfect moves mixed into an otherwise-human game -- exactly the
failure mode we found validating against the Kaggle dataset, where
"cheating" often means using an engine on only some moves.

PERFECT_MOVE_THRESHOLD: a move counts as "perfect" if its centipawn loss is
at or below this. We use a small tolerance (not exactly 0) because engine
analysis at fixed depth has minor noise -- see the earlier lesson about
transposition-table state affecting exact evaluations.
"""

PERFECT_MOVE_THRESHOLD = 5
WINDOW_SIZE = 10


def windowed_features(cp_loss_sequence: list, window: int = WINDOW_SIZE) -> dict:
    n = len(cp_loss_sequence)
    if n == 0:
        return {
            "max_window_match_rate": 0.0,
            "min_window_avg_cp_loss": 0.0,
            "perfect_move_frac": 0.0,
            "longest_perfect_streak": 0,
        }

    # If the game is shorter than one window, treat the whole game as
    # a single window rather than producing no windows at all.
    w = min(window, n)

    window_match_rates = []
    window_avg_losses = []
    for start in range(0, n - w + 1):
        chunk = cp_loss_sequence[start:start + w]
        match_count = sum(1 for cp in chunk if cp <= PERFECT_MOVE_THRESHOLD)
        window_match_rates.append(100 * match_count / w)
        window_avg_losses.append(sum(chunk) / w)

    perfect_flags = [cp <= PERFECT_MOVE_THRESHOLD for cp in cp_loss_sequence]
    perfect_frac = sum(perfect_flags) / n

    longest_streak = 0
    current_streak = 0
    for is_perfect in perfect_flags:
        current_streak = current_streak + 1 if is_perfect else 0
        longest_streak = max(longest_streak, current_streak)

    return {
        "max_window_match_rate": round(max(window_match_rates), 1),
        "min_window_avg_cp_loss": round(min(window_avg_losses), 1),
        "perfect_move_frac": round(perfect_frac, 3),
        "longest_perfect_streak": longest_streak,
    }
