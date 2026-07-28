from __future__ import annotations

import argparse
import unittest

from capacity_model import availability, storage, traffic


class CapacityModelTests(unittest.TestCase):
    def test_peak_rps_and_bandwidth(self) -> None:
        result = traffic(
            argparse.Namespace(
                requests=600.0,
                active_seconds=60.0,
                peak_factor=4.0,
                request_bytes=100.0,
                response_bytes=900.0,
            )
        )
        self.assertEqual(result["results"]["peak_rps"], 40.0)
        self.assertEqual(result["results"]["peak_bandwidth_bytes_per_second"], 40000.0)

    def test_storage_includes_replication_and_index(self) -> None:
        result = storage(
            argparse.Namespace(
                objects_per_day=10.0,
                object_bytes=100.0,
                retention_days=2.0,
                replication_factor=3.0,
                index_overhead=0.5,
            )
        )
        self.assertEqual(result["results"]["total_bytes"], 9000.0)

    def test_availability_uses_visible_formula(self) -> None:
        result = availability(argparse.Namespace(target=99.9))
        self.assertGreater(result["results"]["annual_downtime_minutes"], 500)


if __name__ == "__main__":
    unittest.main()
