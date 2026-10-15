import unittest

from ipc_engine import run_benchmark, run_race


class EngineTests(unittest.TestCase):
    def test_all_ipc_methods_transfer_data(self):
        for method in ("pipe", "queue", "shared_memory", "socket"):
            with self.subTest(method=method):
                result = run_benchmark(method, messages=20, payload_size=128)
                self.assertEqual(result["bytes_transferred"], 2560)
                self.assertEqual(result["received_bytes"], 2560)
                self.assertTrue(result["verified"])
                self.assertGreater(result["messages_per_second"], 0)
                self.assertTrue(result["worker_pids"])

    def test_lock_produces_exact_counter(self):
        result = run_race(workers=3, iterations=200, synchronized=True)
        self.assertEqual(result["actual"], result["expected"])
        self.assertEqual(result["lost_updates"], 0)

    def test_unprotected_counter_exposes_lost_updates(self):
        result = run_race(workers=3, iterations=200, synchronized=False)
        self.assertLess(result["actual"], result["expected"])
        self.assertGreater(result["lost_updates"], 0)

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            run_benchmark("telepathy", messages=10, payload_size=10)


if __name__ == "__main__":
    unittest.main()
