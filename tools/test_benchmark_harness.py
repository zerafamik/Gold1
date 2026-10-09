#!/usr/bin/env python3
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
"""Regression tests for portability, thread budgets, and robust calibration."""
from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

import interval_bench
import crossover
import matrix


class ThreadPlanTests(unittest.TestCase):
    def test_even_budgets_split_exactly(self):
        expected = {2: (1, 1), 4: (2, 2), 6: (3, 3), 8: (4, 4), 12: (6, 6)}
        for total, (high, low) in expected.items():
            with self.subTest(total=total):
                plan = interval_bench.thread_plan(total)
                self.assertEqual(plan["total"], total)
                self.assertEqual((plan["concurrent_high"], plan["concurrent_low"]),
                                 (high, low))
                self.assertEqual(high + low, total)
                self.assertEqual(plan["sequential_per_endpoint"], total)

    def test_odd_budget_is_not_oversubscribed(self):
        plan = interval_bench.thread_plan(5)
        self.assertEqual((plan["concurrent_high"], plan["concurrent_low"]), (2, 3))
        self.assertEqual(plan["concurrent_high"] + plan["concurrent_low"], 5)

    def test_small_budget_rejected(self):
        with self.assertRaises(ValueError):
            interval_bench.thread_plan(1)

    def test_modes_reflect_selected_budget(self):
        self.assertEqual(interval_bench.endpoint_pair_modes(4),
                         ("sequential_4+4", "concurrent_2+2"))


class ComparatorProtocolTests(unittest.TestCase):
    def setUp(self):
        self.old_threads = interval_bench.THREADS
        interval_bench.THREADS = 4

    def tearDown(self):
        interval_bench.THREADS = self.old_threads

    def test_calibration_uses_two_plus_two_at_four_threads(self):
        calls = []
        concurrent_times = iter([1.00, 1.10, 0.90])
        sequential_times = iter([2.00, 2.10, 1.90])

        def concurrent(task, kind, high, low, timeout):
            calls.append((kind, high, low, timeout))
            return {"ok": True, "seconds": next(concurrent_times)}

        def sequential(task, timeout):
            return {"ok": True, "seconds": next(sequential_times)}

        with mock.patch.object(interval_bench, "primecount_sequential",
                               side_effect=sequential), \
             mock.patch.object(interval_bench, "pair_concurrent", side_effect=concurrent), \
             mock.patch.object(interval_bench, "fastprime_available", return_value=False), \
             mock.patch.dict(os.environ, {
                 "GOLD1_PROTOCOL_CALIBRATION_REPEATS": "3",
                 "GOLD1_PROTOCOL_TIE_BREAK_REPEATS": "2",
                 "GOLD1_PROTOCOL_NEAR_TIE": "0.02",
             }), \
             contextlib.redirect_stdout(io.StringIO()):
            mode, fast_mode, calibration = interval_bench.calibrate(object(), timeout=17)

        self.assertEqual(mode, "concurrent_2+2")
        self.assertIsNone(fast_mode)
        self.assertEqual(calls, [("primecount", 2, 2, 17)] * 3)
        self.assertEqual(calibration["thread_plan"]["total"], 4)
        self.assertEqual(calibration["primecount"]["base_repeats"], 3)
        self.assertEqual(calibration["primecount"]["total_repeats"], 3)
        self.assertEqual(calibration["primecount"]["sequential_median"], 2.0)
        self.assertEqual(calibration["primecount"]["concurrent_median"], 1.0)

    def test_near_tie_still_selects_lower_median(self):
        selected, summary = interval_bench.select_endpoint_protocol(
            [10.0, 10.1, 9.9], [9.85, 9.95, 9.90],
            "sequential_4+4", "concurrent_2+2", 0.02,
        )
        self.assertEqual(selected, "concurrent_2+2")
        self.assertTrue(summary["near_tie"])

    def test_material_concurrent_gain_is_selected(self):
        selected, summary = interval_bench.select_endpoint_protocol(
            [10.0, 10.1, 9.9], [9.0, 9.1, 8.9],
            "sequential_4+4", "concurrent_2+2", 0.02,
        )
        self.assertEqual(selected, "concurrent_2+2")
        self.assertGreater(summary["concurrent_relative_gain"], 0.02)

    def test_invalid_calibration_policy_rejected(self):
        with mock.patch.dict(os.environ, {
            "GOLD1_PROTOCOL_CALIBRATION_REPEATS": "0",
            "GOLD1_PROTOCOL_TIE_BREAK_REPEATS": "2",
            "GOLD1_PROTOCOL_NEAR_TIE": "0.02",
        }):
            with self.assertRaisesRegex(ValueError, "REPEATS"):
                interval_bench.calibration_policy()

    def test_near_tie_triggers_adaptive_tie_breaks(self):
        concurrent_calls = []
        sequential_times = iter([10.0, 10.1, 9.9, 10.0, 10.0])
        concurrent_times = iter([9.95, 9.9, 9.95, 9.7, 9.8])

        def sequential(task, timeout):
            return {"ok": True, "seconds": next(sequential_times)}

        def concurrent(task, kind, high, low, timeout):
            concurrent_calls.append((kind, high, low, timeout))
            return {"ok": True, "seconds": next(concurrent_times)}

        with mock.patch.object(interval_bench, "primecount_sequential",
                               side_effect=sequential), \
             mock.patch.object(interval_bench, "pair_concurrent",
                               side_effect=concurrent), \
             contextlib.redirect_stdout(io.StringIO()):
            selected, summary = interval_bench.calibrate_implementation(
                object(), "primecount", 23, 3, 2, 0.02,
                interval_bench.thread_plan(4), "sequential_4+4", "concurrent_2+2",
            )

        self.assertEqual(selected, "concurrent_2+2")
        self.assertTrue(summary["initial_near_tie"])
        self.assertEqual(summary["tie_break_repeats_performed"], 2)
        self.assertEqual(summary["total_repeats"], 5)
        self.assertEqual(concurrent_calls, [("primecount", 2, 2, 23)] * 5)

    def test_selected_concurrent_run_uses_current_split(self):
        task = object()
        with mock.patch.object(interval_bench, "pair_concurrent",
                               return_value={"ok": True, "seconds": 1.0}) as concurrent:
            interval_bench.run_selected(task, "primecount", "concurrent_2+2", 19)
        concurrent.assert_called_once_with(task, "primecount", 2, 2, 19)

    def test_stale_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            interval_bench.run_selected(object(), "primecount", "concurrent_6+6", 19)


class MatrixLauncherTests(unittest.TestCase):
    def test_schema_versions_match(self):
        self.assertEqual(matrix.SCHEMA_VERSION, interval_bench.SCHEMA_VERSION)
        self.assertEqual(matrix.SCHEMA_VERSION,
                         "2.3.6-robust-calibration-crossover")

    def test_child_uses_same_python_not_shell_script(self):
        command = matrix.benchmark_command(10, 20, 7)
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], str(matrix.BENCHMARK))
        self.assertEqual(command[2:], ["benchmark", "10", "20", "--runs", "7"])
        self.assertFalse(any(part.endswith(".sh") for part in command))

    def test_crossover_matrix_brackets_estimated_boundary(self):
        widths = [high - low for low, high, _ in crossover.CROSSOVER_MATRIX]
        self.assertEqual(widths, [125_000_000_000, 150_000_000_000,
                                  175_000_000_000, 200_000_000_000])
        self.assertTrue(all(low == 10**18 for low, _, _ in crossover.CROSSOVER_MATRIX))

    def test_crossover_uses_separate_aggregate_name(self):
        with mock.patch.object(crossover.matrix, "main") as runner:
            crossover.main()
        runner.assert_called_once_with(crossover.CROSSOVER_MATRIX,
                                       suite_name="crossover_matrix")


if __name__ == "__main__":
    unittest.main(verbosity=2)
