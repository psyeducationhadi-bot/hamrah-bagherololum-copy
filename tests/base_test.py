"""Base test class providing safe assertion helpers for E2E tests.

Prevents standard library unittest from dumping megabyte-sized HTML strings into
terminal outputs when regex or containment assertions fail.
"""

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class BaseE2ETest(unittest.TestCase):
    root = PROJECT_ROOT
    index_path = root / "index.html"
    manifest_path = root / "manifest.json"
    sw_path = root / "sw.js"
    offline_path = root / "offline.html"
    keystore_txt_path = root / "KEYSTORE_CREDENTIALS.txt"
    keystore_path = root / "android.keystore"
    assetlinks_path = root / ".well-known" / "assetlinks.json"
    nojekyll_path = root / ".nojekyll"
    wrangler_path = root / "wrangler.json"
    workflow_path = root / ".github" / "workflows" / "build-android-apk.yml"
    android_dir = root / "android"
    release_apk_dir = root / "release-apk"

    def assert_matches(self, pattern, text, msg=None, flags=0):
        """Assert regex pattern matches text without dumping full text on failure."""
        match = re.search(pattern, text, flags)
        self.assertTrue(bool(match), msg or f"Pattern '{pattern}' did not match")

    def assert_not_matches(self, pattern, text, msg=None, flags=0):
        """Assert regex pattern does NOT match text without dumping full text on failure."""
        match = re.search(pattern, text, flags)
        self.assertFalse(bool(match), msg or f"Pattern '{pattern}' unexpectedly matched")

    def assert_in_text(self, member, text, msg=None):
        """Assert substring in text without dumping full text on failure."""
        self.assertTrue(member in text, msg or f"'{member}' not found in target text")

    def assert_not_in_text(self, member, text, msg=None):
        """Assert substring not in text without dumping full text on failure."""
        self.assertFalse(member in text, msg or f"'{member}' unexpectedly found in target text")
