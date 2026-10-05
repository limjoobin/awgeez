import unittest
from uuid import uuid4

import redis

from graph.preferences import PreferenceGraph
from storage import MemoryStore, RedisStore


def sample_graph() -> PreferenceGraph:
    return PreferenceGraph(
        {"u1": ["v2", "v1"], "u2": [], "u3": ["v1"]},
        {"v1": ["u3", "u1"], "v2": ["u1"]},
    )


class MemoryStoreTests(unittest.TestCase):
    def test_queries_round_trip_and_result_replacement(self):
        store = MemoryStore()
        with self.assertRaises(KeyError):
            store.load_graph()
        store.replace_graph(sample_graph(), {"wave": 7})
        self.assertEqual(store.load_graph().edges, sample_graph().edges)
        self.assertEqual(store.metadata(), {"wave": 7})
        self.assertEqual(store.ranked("u1"), [("v2", 1), ("v1", 2)])
        self.assertEqual(store.ranked("u1", top_k=1), [("v2", 1)])
        self.assertEqual(store.ranked("u1", max_rank=1), [("v2", 1)])
        self.assertEqual(store.ranked("u2"), [])
        self.assertEqual(store.pair_rank("u1", "v1"), 2)
        self.assertIsNone(store.pair_rank("u2", "v1"))
        store.save_result("gale_shapley_u_proposes", {"stable": True})
        self.assertEqual(store.load_result("gale_shapley_u_proposes"), {"stable": True})
        store.replace_graph(sample_graph())
        self.assertEqual(store.result_names(), [])


class RedisStoreTests(unittest.TestCase):
    def setUp(self):
        client = redis.Redis.from_url(
            "redis://127.0.0.1:6379/0", decode_responses=True, socket_timeout=2
        )
        try:
            client.ping()
        except redis.RedisError:
            self.skipTest("Redis is not running on localhost:6379")
        self.store = RedisStore(f"test-{uuid4().hex}", client=client)

    def tearDown(self):
        if hasattr(self, "store"):
            self.store.clear_namespace()

    def test_sorted_sets_queries_results_and_graph_round_trip(self):
        store = self.store
        graph = sample_graph()
        store.replace_graph(graph, {"source": "test"}, ranking_scores={
            "like": {"u1": {"v2": 8.0, "v1": 7.0}},
            "attributes": {"u1": {"v2": 7.5, "v1": 8.5}},
        })
        self.assertEqual(store.client.type(store._key("prefs:u1")), "zset")
        self.assertEqual(
            store.client.zrange(store._key("prefs:u1"), 0, -1, withscores=True),
            [("v2", 1.0), ("v1", 2.0)],
        )
        self.assertEqual(store.load_graph().edges, graph.edges)
        self.assertEqual(store.metadata(), {"source": "test"})
        self.assertEqual(store.client.type(store._key("scores:like:u1")), "zset")
        self.assertEqual(store.pair_scores("u1", "v2"), {"like": 8.0, "attributes": 7.5})
        self.assertEqual(store.ranked("u1", top_k=1), [("v2", 1)])
        self.assertEqual(store.ranked("u1", max_rank=1), [("v2", 1)])
        self.assertEqual(store.ranked("u1", top_k=1, max_rank=2), [("v2", 1)])
        self.assertEqual(store.ranked("u2"), [])
        self.assertEqual(store.pair_rank("u1", "v1"), 2)
        self.assertIsNone(store.pair_rank("u2", "v1"))
        store.save_result("minimum_regret", {"maximum_regret": 2})
        self.assertEqual(store.result_names(), ["minimum_regret"])
        self.assertEqual(store.load_result("minimum_regret"), {"maximum_regret": 2})
        store.replace_graph(graph)
        self.assertEqual(store.result_names(), [])
        self.assertIsNone(store.load_result("minimum_regret"))
        self.assertEqual(store.pair_scores("u1", "v2"), {"like": None, "attributes": None})

    def test_empty_graph_round_trip(self):
        empty = PreferenceGraph({}, {"v1": []})
        self.store.replace_graph(empty)
        restored = self.store.load_graph()
        self.assertEqual(restored.u, ())
        self.assertEqual(restored.v, ("v1",))
        self.assertEqual(self.store.ranked("v1"), [])
