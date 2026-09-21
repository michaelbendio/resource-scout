import importlib.util
from pathlib import Path
from decimal import Decimal
import unittest


spec = importlib.util.spec_from_file_location('deepseek_trial', Path(__file__).resolve().parents[1] / 'scripts/deepseek-challenger-trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class TrialBudgetTests(unittest.TestCase):
    def test_peak_reservation_includes_full_output_and_input(self):
        payload = {'messages': [{'content': 'ä' * 10000}], 'max_tokens': 32768}
        reserve = trial.reserve_cost(payload)
        self.assertGreater(reserve, Decimal('0.047'))
        self.assertLess(reserve, Decimal('0.06'))

    def test_cached_usage_is_not_charged_twice(self):
        cost = trial.usage_cost({'prompt_tokens': 100000, 'prompt_cache_hit_tokens': 90000, 'prompt_cache_miss_tokens': 10000, 'completion_tokens': 10000})
        self.assertEqual(cost, Decimal('0.01554'))

    def test_uncached_usage_fallback(self):
        cost = trial.usage_cost({'prompt_tokens': 100000, 'completion_tokens': 10000})
        self.assertEqual(cost, Decimal('0.042'))

    def test_delayed_account_balance_cannot_hide_spend(self):
        self.assertFalse(trial.budget_allows(Decimal('7.54'), Decimal('7.54'), Decimal('7.20'), Decimal('0.10')))

    def test_other_account_spend_preserves_reserve(self):
        self.assertFalse(trial.budget_allows(Decimal('0.30'), Decimal('7.54'), Decimal('0.10'), Decimal('0.10')))

    def test_reject_incomplete_lead(self):
        with self.assertRaises(ValueError):
            trial.validate_result({'leads': [{'organization': 'A'}]})

    def test_reject_extra_top_level_fields(self):
        with self.assertRaises(ValueError):
            trial.validate_result({'leads': [], 'commentary': 'not in schema'})


if __name__ == '__main__':
    unittest.main()
