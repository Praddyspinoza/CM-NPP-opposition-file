import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RefreshContractTests(unittest.TestCase):
    def test_early_backup_schedules_and_external_trigger(self):
        workflow = (ROOT / '.github/workflows/daily-update.yml').read_text()
        self.assertIn("cron: '13 23 * * *'", workflow)
        self.assertIn("cron: '17 0 * * *'", workflow)
        self.assertIn('workflow_dispatch:', workflow)
        self.assertIn('cancel-in-progress: false', workflow)
        self.assertIn('contents: write', workflow)
        self.assertIn('git add data/feed.json', workflow)
        self.assertIn('Validate refreshed feed', workflow)

    def test_dashboard_and_collector_data_contract_is_preserved(self):
        script = (ROOT / 'scripts/update.py').read_text()
        page = (ROOT / 'index.html').read_text()
        self.assertIn("'generated_at'", script)
        self.assertIn("'items'", script)
        self.assertIn('data/feed.json?ts=', page)


if __name__ == '__main__':
    unittest.main()
