import unittest
from datetime import date

from scripts.profile_metrics import calculate_streaks


def contribution(day: str, count: int = 1) -> dict[str, object]:
    return {"date": day, "contributionCount": count}


class ContributionStreakTests(unittest.TestCase):
    def test_empty_calendar_has_no_streaks(self) -> None:
        self.assertEqual(calculate_streaks([], date(2026, 11, 27)), (0, 0))

    def test_current_streak_includes_today(self) -> None:
        items = [
            contribution("2026-11-24"),
            contribution("2026-11-25"),
            contribution("2026-11-26"),
            contribution("2026-11-27"),
        ]
        self.assertEqual(calculate_streaks(items, date(2026, 11, 27)), (4, 4))

    def test_current_streak_accepts_yesterday_as_anchor(self) -> None:
        items = [contribution("2026-11-25"), contribution("2026-11-26")]
        self.assertEqual(calculate_streaks(items, date(2026, 11, 27)), (2, 2))

    def test_old_streak_is_not_reported_as_current(self) -> None:
        items = [
            contribution("2026-11-20"),
            contribution("2026-11-21"),
            contribution("2026-11-22"),
        ]
        self.assertEqual(calculate_streaks(items, date(2026, 11, 27)), (0, 3))

    def test_longest_streak_survives_gaps_and_zero_days(self) -> None:
        items = [
            contribution("2026-11-17"),
            contribution("2026-11-18"),
            contribution("2026-11-19"),
            contribution("2026-11-20", 0),
            contribution("2026-11-21"),
            contribution("2026-11-22"),
            contribution("2026-11-23"),
            contribution("2026-11-24"),
        ]
        self.assertEqual(calculate_streaks(items, date(2026, 11, 24)), (4, 4))

    def test_current_streak_breaks_on_a_missing_day(self) -> None:
        items = [
            contribution("2026-11-20"),
            contribution("2026-11-22"),
            contribution("2026-11-23"),
            contribution("2026-11-24"),
        ]
        self.assertEqual(calculate_streaks(items, date(2026, 11, 24)), (3, 3))


if __name__ == "__main__":
    unittest.main()
