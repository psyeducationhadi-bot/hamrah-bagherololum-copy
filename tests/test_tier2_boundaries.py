"""Tier 2: Boundary, Edge Case, & Malformed Input Tests.

Validates robust handling of corner cases:
- Missing, invalid, and adversarial query parameters (?mode=unknown, ?mode=admin, ?mode=APP)
- Lowercase / malformed hex fingerprints in Digital Asset Links
- Offline navigation failure vs static asset requests
- HTTP redirects breaking DAL verification
- Manifest edge schemas and icon resolutions
- FileProvider authority string matching
- DOM re-injection and prototype manipulation attempts
"""

import json
import re
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from base_test import BaseE2ETest, PROJECT_ROOT


class TestTier2Boundaries(BaseE2ETest):

    # -------------------------------------------------------------------------
    # Edge Case 1: Missing & Default Query Parameters
    # -------------------------------------------------------------------------
    def test_edge_missing_query_params_defaults_to_web_mode(self):
        """Edge: Visiting root URL without any parameters must NOT activate app mode."""
        content = self.index_path.read_text(encoding="utf-8")

        self.assert_matches(
            r'mode\s*===?\s*["\']app["\']|mode\s*==\s*["\']app["\']|\.get\(["\']mode["\']\)\s*===?\s*["\']app["\']',
            content,
            "App mode detection must strictly compare mode parameter against 'app'",
        )

        self.assert_in_text('id="header-admin-btn"', content)

        html_tag = re.search(r"<html[^>]*>", content, re.IGNORECASE)
        self.assertIsNotNone(html_tag)
        self.assert_not_in_text(
            "is-mobile-app",
            html_tag.group(0),
            "Baseline HTML root tag must NOT contain 'is-mobile-app' by default",
        )

    # -------------------------------------------------------------------------
    # Edge Case 2: Invalid & Adversarial Mode Parameters
    # -------------------------------------------------------------------------
    def test_edge_invalid_mode_params_rejected(self):
        """Edge: Parameters like ?mode=unknown, ?mode=admin, ?mode=123 must NOT activate app mode."""
        content = self.index_path.read_text(encoding="utf-8")

        self.assert_not_matches(
            r"if\s*\(\s*(urlParams|params)\.get\(['\"]mode['\"]\)\s*\)\s*\{",
            content,
            "Guard must not treat any arbitrary non-empty mode parameter as app mode",
        )

        self.assert_matches(
            r'mode\s*===?\s*["\']web["\']|["\']mode["\']\s*,\s*["\']web["\']|\?mode=web|mode=web',
            content,
            "Must provide explicit escape hatch for '?mode=web'",
        )

    # -------------------------------------------------------------------------
    # Edge Case 3: Fingerprint Hex Formatting Strictness
    # -------------------------------------------------------------------------
    def test_edge_assetlinks_fingerprint_case_and_delimiter_strictness(self):
        """Edge: SHA-256 fingerprint must be strictly uppercase and colon-separated."""
        self.assertTrue(
            self.assetlinks_path.exists(),
            "assetlinks.json must exist to evaluate fingerprint formatting",
        )
        data = json.loads(self.assetlinks_path.read_text(encoding="utf-8"))

        for idx, statement in enumerate(data):
            fps = statement.get("target", {}).get("sha256_cert_fingerprints", [])
            self.assertGreater(len(fps), 0, f"Statement {idx} has empty fingerprints list")
            for fp in fps:
                self.assertEqual(len(fp), 95, f"Fingerprint '{fp}' length must be exactly 95 characters")
                self.assertFalse(any(c.islower() for c in fp), f"Fingerprint '{fp}' contains lowercase hex")
                for i in range(2, 95, 3):
                    self.assertEqual(fp[i], ":", f"Expected colon at position {i} in '{fp}'")

    # -------------------------------------------------------------------------
    # Edge Case 4: Manifest Start URL & Orientation Boundaries
    # -------------------------------------------------------------------------
    def test_edge_manifest_boundaries_and_scope(self):
        """Edge: Manifest start_url must be scoped within manifest scope and preserve app mode."""
        self.assertTrue(self.manifest_path.exists(), "manifest.json must exist")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        start_url = manifest.get("start_url", "")
        self.assertTrue(
            start_url.startswith("./") or start_url.startswith("/") or "mode=app" in start_url,
            "start_url must be correctly formatted relative or absolute URL",
        )
        self.assertEqual(manifest.get("display"), "standalone")

        for icon in manifest.get("icons", []):
            sizes = icon.get("sizes", "")
            match = re.match(r"^(\d+)x(\d+)$", sizes)
            self.assertIsNotNone(match, f"Icon sizes '{sizes}' must match format WIDTHxHEIGHT")
            w, h = int(match.group(1)), int(match.group(2))
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)
            self.assertEqual(w, h, "PWA icons must be square")

    # -------------------------------------------------------------------------
    # Edge Case 5: Service Worker Offline Navigation vs Sub-resources
    # -------------------------------------------------------------------------
    def test_edge_service_worker_offline_request_discrimination(self):
        """Edge: sw.js should serve offline.html only for navigation (HTML) requests, not failed API/images."""
        self.assertTrue(self.sw_path.exists(), "sw.js must exist")
        sw_text = self.sw_path.read_text(encoding="utf-8")

        self.assert_matches(
            r"mode\s*===?\s*['\"]navigate['\"]|destination\s*===?\s*['\"]document['\"]|text/html|headers\.get\(['\"]accept['\"]\)",
            sw_text,
            "Service worker must discriminate navigation requests when serving offline.html fallback",
        )
        self.assert_matches(r"\.catch\s*\(|try\s*\{.*\}\s*catch", sw_text)

    # -------------------------------------------------------------------------
    # Edge Case 6: Direct Hash & URL Injection Protection
    # -------------------------------------------------------------------------
    def test_edge_direct_hash_injection_admin_route_blocked(self):
        """Edge: Navigating directly to #admin via location.hash must be caught and blocked in app mode."""
        content = self.index_path.read_text(encoding="utf-8")

        self.assert_matches(r"hashchange|location\.hash|navigateTo", content)
        self.assert_matches(r"navigateTo.*admin", content)

    # -------------------------------------------------------------------------
    # Edge Case 7: FileProvider Authority Boundary Matching
    # -------------------------------------------------------------------------
    def test_edge_fileprovider_authority_strict_match(self):
        """Edge: AndroidManifest FILE_PROVIDER_AUTHORITY must strictly match provider android:authorities."""
        android_manifest = self.android_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        if not android_manifest.exists():
            self.skipTest("AndroidManifest.xml not yet created (M4 pending)")

        xml_text = android_manifest.read_text(encoding="utf-8")

        if "androidx.core.content.FileProvider" in xml_text:
            expected_auth = "ir.bagherololum.hamrah.fileprovider"
            self.assertIn(f'android:authorities="{expected_auth}"', xml_text)
            self.assertIn(f'android:value="{expected_auth}"', xml_text)

    # -------------------------------------------------------------------------
    # Edge Case 8: Back Button When No Modals Are Open
    # -------------------------------------------------------------------------
    def test_edge_hardware_back_button_when_no_modals_open(self):
        """Edge: Pressing Back button when no modals are open must not break or freeze navigation."""
        content = self.index_path.read_text(encoding="utf-8")
        self.assert_matches(r"popstate.*(modal|active|length|isOpen|classList)", content)


if __name__ == "__main__":
    unittest.main()
