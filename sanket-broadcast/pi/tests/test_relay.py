"""Unit tests for the local PTT relay policy engine."""
import unittest

from sanket_broadcast.relay import RelayEngine, RelayRule


class RelayEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = RelayEngine([
            RelayRule("mayday", "line-2", ("control", "master", "line-2")),
            RelayRule("control-upstream", "control", ("line-2", "master")),
        ])

    def test_one_to_many_and_source_echo_blocked(self):
        result = self.engine.evaluate({"event_id": "e1", "source": "line-2"})
        self.assertEqual(result.destinations, ["control", "master"])
        self.assertEqual(result.blocked["line-2"], "loop_or_source_echo")

    def test_duplicate_event_is_blocked(self):
        event = {"event_id": "e2", "source": "line-2"}
        self.assertTrue(self.engine.evaluate(event).allowed)
        duplicate = self.engine.evaluate(event)
        self.assertFalse(duplicate.allowed)
        self.assertEqual(duplicate.blocked["*"], "duplicate_event")

    def test_relay_path_prevents_loop(self):
        event = {
            "event_id": "e3", "source": "control", "origin_channel": "line-2",
            "relay_path": ["line-2", "control"], "relay_hops": 1,
        }
        result = self.engine.evaluate(event)
        self.assertNotIn("line-2", result.destinations)
        self.assertEqual(result.destinations, ["master"])

    def test_hop_limit(self):
        engine = RelayEngine([RelayRule("short", "a", ("b",), max_hops=2)])
        result = engine.evaluate({"event_id": "e4", "source": "a", "relay_hops": 2})
        self.assertFalse(result.allowed)
        self.assertEqual(result.blocked["short"], "hop_limit")

    def test_missing_source_is_rejected(self):
        result = self.engine.evaluate({"event_id": "e5"})
        self.assertFalse(result.allowed)
        self.assertEqual(result.blocked["*"], "missing_source")

    def test_forwarded_metadata_preserves_origin_and_path(self):
        event = {"source": "line-2", "origin_channel": "line-2", "relay_hops": 0}
        metadata = RelayEngine.relay_metadata(event, "control", "e6")
        self.assertEqual(metadata["origin_channel"], "line-2")
        self.assertEqual(metadata["relay_path"], ["line-2"])
        self.assertEqual(metadata["relay_hops"], 1)


if __name__ == "__main__":
    unittest.main()
