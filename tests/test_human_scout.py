from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from resource_research_agent.human_scout import prepare_database
from resource_research_agent.storage import ResearchStore


class HumanScoutIsolationTests(unittest.TestCase):
    def test_fresh_database_is_an_independent_human_configured_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "production.sqlite3"
            target = root / "human.sqlite3"
            production = ResearchStore(source)
            production.save_settings({"adapter": "demo", "dshConfiguration": "local-qwen"})

            prepared = prepare_database(source, target, fresh=True)

            self.assertEqual(target.resolve(), prepared)
            self.assertEqual("demo", production.get_settings()["adapter"])
            temporary = ResearchStore(target)
            self.assertEqual("dsh", temporary.get_settings()["adapter"])
            self.assertEqual("human", temporary.get_settings()["dshConfiguration"])
            self.assertEqual([], temporary.list_runs())
            self.assertNotEqual(source.stat().st_ino, target.stat().st_ino)


if __name__ == "__main__":
    unittest.main()

