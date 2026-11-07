#!/usr/bin/env python3
"""Unified E2E Test Suite Runner for Hamrah Bagherololum Copy (PWA & Android TWA).

Supports 4-tier requirement verification:
  Tier 1: Feature coverage (Features 1-26)
  Tier 2: Boundary & Corner cases
  Tier 3: Cross-feature combinations & contracts
  Tier 4: Real-world application scenarios

Usage:
  python tests/run_e2e_tests.py                 # Run full suite (Tiers 1-4)
  python tests/run_e2e_tests.py --tier 1        # Run only Tier 1
  python tests/run_e2e_tests.py --milestone M1  # Run tests for Milestone 1
  python tests/run_e2e_tests.py --feature F-05  # Run tests for Feature 5
  python tests/run_e2e_tests.py --json          # Machine-readable JSON output
  python tests/run_e2e_tests.py -v              # Verbose mode
"""

import argparse
import io
import json
import os
import re
import sys
import time
import unittest
from pathlib import Path

# Fix Windows console UTF-8 output encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root and tests directory to sys.path
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import test modules
import test_tier1_features
import test_tier2_boundaries
import test_tier3_combinations
import test_tier4_scenarios

FEATURE_MILESTONE_MAP = {
    "F-01": "M1", "F-02": "M1", "F-03": "M1", "F-04": "M1", "F-05": "M1", "F-06": "M1",
    "F-07": "M2", "F-08": "M2", "F-09": "M2", "F-10": "M2", "F-11": "M2", "F-12": "M2",
    "F-13": "M3", "F-14": "M3", "F-15": "M3", "F-16": "M3", "F-17": "M3", "F-18": "M3", "F-19": "M3",
    "F-20": "M4", "F-21": "M4", "F-22": "M4", "F-23": "M4",
    "F-24": "M5", "F-25": "M5", "F-26": "M5",
    "F-27": "M6", "F-28": "M6",
}


def build_suite(tier=None, milestone=None, feature=None):
    """Build a filtered unittest.TestSuite based on CLI arguments."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Determine which tiers to include
    include_tier1 = tier in (None, "all", "1")
    include_tier2 = tier in (None, "all", "2")
    include_tier3 = tier in (None, "all", "3")
    include_tier4 = tier in (None, "all", "4")

    # Load Tier 1
    if include_tier1:
        t1_tests = loader.loadTestsFromTestCase(test_tier1_features.TestTier1Features)
        for t in t1_tests:
            name = t._testMethodName
            m = re.search(r"test_f(\d\d)_", name)
            f_id = f"F-{m.group(1)}" if m else None

            if feature and f_id != feature:
                continue
            if milestone and f_id and FEATURE_MILESTONE_MAP.get(f_id) != milestone:
                continue
            suite.addTest(t)

    # Load Tier 2
    if include_tier2 and not feature and not milestone:
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2Boundaries))

    # Load Tier 3
    if include_tier3 and not feature and not milestone:
        suite.addTests(loader.loadTestsFromTestCase(test_tier3_combinations.TestTier3Combinations))

    # Load Tier 4
    if include_tier4 and not feature and not milestone:
        suite.addTests(loader.loadTestsFromTestCase(test_tier4_scenarios.TestTier4Scenarios))

    return suite


class DetailedTestResult(unittest.TestResult):
    def __init__(self, stream=None, descriptions=None, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.verbosity = verbosity
        self.stream = stream or sys.stdout
        self.test_records = []

    def startTest(self, test):
        super().startTest(test)
        if self.verbosity > 1:
            doc = test.shortDescription() or test._testMethodName
            self.stream.write(f"  [RUNNING] {test._testMethodName}: {doc}... ")
            self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_records.append({
            "test": test._testMethodName,
            "doc": test.shortDescription(),
            "module": test.__class__.__module__,
            "status": "PASS",
            "message": "",
        })
        if self.verbosity > 1:
            self.stream.write("[PASS]\n")
        elif self.verbosity == 1:
            self.stream.write(".")
            self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        msg = self._exc_info_to_string(err, test)
        lines = msg.splitlines()
        trimmed = [l[:300] + "... [truncated]" if len(l) > 300 else l for l in lines]
        msg = "\n".join(trimmed)
        self.test_records.append({
            "test": test._testMethodName,
            "doc": test.shortDescription(),
            "module": test.__class__.__module__,
            "status": "FAIL",
            "message": msg,
        })
        if self.verbosity > 1:
            self.stream.write("[FAIL]\n")
        elif self.verbosity == 1:
            self.stream.write("F")
            self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        msg = self._exc_info_to_string(err, test)
        lines = msg.splitlines()
        trimmed = [l[:300] + "... [truncated]" if len(l) > 300 else l for l in lines]
        msg = "\n".join(trimmed)
        self.test_records.append({
            "test": test._testMethodName,
            "doc": test.shortDescription(),
            "module": test.__class__.__module__,
            "status": "ERROR",
            "message": msg,
        })
        if self.verbosity > 1:
            self.stream.write("[ERROR]\n")
        elif self.verbosity == 1:
            self.stream.write("E")
            self.stream.flush()

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_records.append({
            "test": test._testMethodName,
            "doc": test.shortDescription(),
            "module": test.__class__.__module__,
            "status": "SKIP",
            "message": reason,
        })
        if self.verbosity > 1:
            self.stream.write(f"[SKIP: {reason}]\n")
        elif self.verbosity == 1:
            self.stream.write("s")
            self.stream.flush()


def main():
    parser = argparse.ArgumentParser(
        description="Hamrah Bagherololum Copy E2E Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all",
                        help="Filter execution to specific test tier (default: all)")
    parser.add_argument("--milestone", choices=["M1", "M2", "M3", "M4", "M5", "M6"],
                        help="Filter Tier 1 execution to a specific milestone (e.g. M1, M2)")
    parser.add_argument("--feature", help="Filter Tier 1 execution to a specific feature ID (e.g. F-05)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose test output")
    parser.add_argument("--json", action="store_true", help="Emit JSON output summary")

    args = parser.parse_args()

    verbosity = 0 if args.json else (2 if args.verbose else 1)
    stream = sys.stdout

    start_time = time.time()
    suite = build_suite(tier=args.tier, milestone=args.milestone, feature=args.feature)

    total_tests = suite.countTestCases()

    if not args.json:
        print("=" * 78)
        print(" HAMRAH BAGHEROLOLUM COPY -- END-TO-END VERIFICATION TEST SUITE")
        print("=" * 78)
        print(f" Target Project Root : {PROJECT_ROOT}")
        print(f" Execution Scope     : Tier={args.tier or 'all'}, Milestone={args.milestone or 'all'}, Feature={args.feature or 'all'}")
        print(f" Total Tests Queued  : {total_tests}")
        print("-" * 78)

    result = DetailedTestResult(stream=stream, verbosity=verbosity)
    suite.run(result)
    elapsed = time.time() - start_time

    if not args.json:
        if verbosity == 1:
            print()
        print("-" * 78)

        # Print failures and errors detail if any
        if result.failures:
            print("\nFAILED TESTS:")
            for test, msg in result.failures:
                print(f"\n--- {test} ---")
                try:
                    print(msg.strip())
                except Exception:
                    print(msg.encode("ascii", errors="replace").decode("ascii").strip())

        if result.errors:
            print("\nTEST ERRORS:")
            for test, msg in result.errors:
                print(f"\n--- {test} ---")
                try:
                    print(msg.strip())
                except Exception:
                    print(msg.encode("ascii", errors="replace").decode("ascii").strip())

        # Tier breakdown
        t1_count = len([r for r in result.test_records if "tier1" in r["module"]])
        t2_count = len([r for r in result.test_records if "tier2" in r["module"]])
        t3_count = len([r for r in result.test_records if "tier3" in r["module"]])
        t4_count = len([r for r in result.test_records if "tier4" in r["module"]])

        print("\nSUMMARY BY TIER:")
        print(f"  Tier 1 (Feature Coverage)        : {t1_count} tests executed")
        print(f"  Tier 2 (Boundaries & Edge Cases) : {t2_count} tests executed")
        print(f"  Tier 3 (Cross-Feature Contracts) : {t3_count} tests executed")
        print(f"  Tier 4 (Real-World Scenarios)    : {t4_count} tests executed")
        print("-" * 78)

        passed = len([r for r in result.test_records if r["status"] == "PASS"])
        failed = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)

        status_str = f"{passed} PASSED, {failed} FAILED, {errors} ERRORS, {skipped} SKIPPED"
        print(f"RESULT: {status_str} in {elapsed:.2f}s")
        print("=" * 78)

    if args.json:
        output_payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total": total_tests,
            "passed": len([r for r in result.test_records if r["status"] == "PASS"]),
            "failed": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "elapsed_seconds": round(elapsed, 3),
            "records": result.test_records,
        }
        print(json.dumps(output_payload, indent=2))

    sys.exit(1 if (result.failures or result.errors) else 0)


if __name__ == "__main__":
    main()
