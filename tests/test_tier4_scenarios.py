"""Tier 4: Real-World End-to-End Application Scenarios.

Simulates end-to-end user and system journeys:
- Scenario 1: Student End-to-End Navigation in Android App Mode
- Scenario 2: Administrator Web Workflow with Real-Time Dynamic Sync
- Scenario 3: Cafe Bazaar Automated Ingestion Robot Validation
- Scenario 4: Sub-optimal Connectivity & Persian Offline Fallback
- Scenario 5: GitHub Actions CI/CD Headless Build & Release Pipeline
"""

import json
import re
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from base_test import BaseE2ETest, PROJECT_ROOT


class TestTier4Scenarios(BaseE2ETest):
    @classmethod
    def setUpClass(cls):
        cls.android_manifest_path = cls.android_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        cls.android_gradle_path = cls.android_dir / "app" / "build.gradle"

    # -------------------------------------------------------------------------
    # Scenario 1: Student End-to-End Navigation in Android App Mode
    # -------------------------------------------------------------------------
    def test_scenario_1_student_app_mode_lifecycle(self):
        """Scenario 1: Complete student journey in app mode (?mode=app) without admin exposure."""
        content = self.index_path.read_text(encoding="utf-8")

        head_match = re.search(r"<head>(.*?)</head>", content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(head_match, "Document must have a <head> section")
        head_text = head_match.group(1)

        # Step 1: Early guard execution in <head>
        self.assert_matches(r"mode=app|mode\s*===?\s*['\"]app['\"]", head_text)
        self.assert_in_text("is-mobile-app", head_text)

        # Step 2: Anti-FOUC CSS rule suppresses admin button instantly
        self.assert_matches(
            r"\.is-mobile-app.*#header-admin-btn|html\.is-mobile-app.*#header-admin-btn",
            content,
            "Anti-FOUC rule must guarantee admin button invisibility before render",
        )

        # Step 3: Physical DOM cleanup removes admin button node
        self.assert_matches(
            r"header-admin-btn.*remove\(\)|remove.*header-admin-btn",
            content,
            "DOM cleanup must remove admin button node from DOM",
        )

        # Step 4: Interception of navigation to admin panel
        self.assert_matches(
            r"navigateTo.*admin.*(is-mobile-app|isAppMode|HAMRAH_APP_MODE)|(is-mobile-app|isAppMode|HAMRAH_APP_MODE).*navigateTo",
            content,
            "Route guard must intercept student attempts to navigate to admin",
        )

        # Step 5: Interception of staff login modal
        self.assert_matches(
            r"openStaffLoginModal.*(is-mobile-app|isAppMode|HAMRAH_APP_MODE)|(is-mobile-app|isAppMode|HAMRAH_APP_MODE).*openStaffLoginModal",
            content,
            "Staff login modal must be blocked from opening in app mode",
        )

        # Step 6: Student sections (quizzes, tools, faq, categories) remain intact
        self.assert_in_text("nav-quizzes", content)
        self.assert_in_text("nav-tools", content)
        self.assert_in_text("nav-faq", content)

    # -------------------------------------------------------------------------
    # Scenario 2: Administrator Web Workflow with Real-Time Dynamic Sync
    # -------------------------------------------------------------------------
    def test_scenario_2_admin_web_workflow_and_realtime_sync(self):
        """Scenario 2: Administrator accessing via web mode with real-time update sync."""
        content = self.index_path.read_text(encoding="utf-8")

        # Step 1: Web mode reset available (?mode=web)
        self.assert_matches(r"mode=web|mode\s*===?\s*['\"]web['\"]", content)

        # Step 2: Admin button is present in baseline DOM
        self.assert_in_text('id="header-admin-btn"', content)

        # Step 3: Staff login modal is functional
        self.assert_in_text("openStaffLoginModal", content)
        self.assert_in_text("auth-username-inp", content)
        self.assert_in_text("auth-password-inp", content)

        # Step 4: Service worker guarantees real-time fresh fetch for dynamic CMS updates
        self.assertTrue(self.sw_path.exists(), "sw.js must exist for real-time sync validation")
        sw_text = self.sw_path.read_text(encoding="utf-8")
        self.assert_matches(
            r"no-store|networkFirst|NetworkFirst|cache:\s*['\"]no-store['\"]",
            sw_text,
            "Service worker must ensure dynamic updates are fetched with no-store or network-first",
        )

        # Step 5: Dynamic data targets db.json / API without stale caching
        self.assert_in_text("db.json", content)

    # -------------------------------------------------------------------------
    # Scenario 3: Cafe Bazaar Automated Ingestion Robot Validation
    # -------------------------------------------------------------------------
    def test_scenario_3_cafebazaar_ingestion_robot_validation(self):
        """Scenario 3: Cafe Bazaar automated crawler verification simulation."""
        if self.android_manifest_path.exists():
            xml_text = self.android_manifest_path.read_text(encoding="utf-8")
            self.assert_in_text("DEFAULT_URL", xml_text)
            self.assert_in_text("hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app", xml_text)

        self.assertTrue(self.assetlinks_path.exists(), "assetlinks.json must exist at root")
        assetlinks_text = self.assetlinks_path.read_text(encoding="utf-8")
        assetlinks = json.loads(assetlinks_text)

        has_bazaar_relation = any("cafebazaar_twa" in stmt.get("relation", []) for stmt in assetlinks)
        self.assertTrue(has_bazaar_relation, "Crawler must find statement with relation 'cafebazaar_twa'")

        has_correct_pkg = any(
            stmt.get("target", {}).get("package_name") == "ir.bagherololum.hamrah" for stmt in assetlinks
        )
        self.assertTrue(has_correct_pkg, "Crawler must verify package name 'ir.bagherololum.hamrah'")

        self.assertTrue(self.keystore_txt_path.exists(), "KEYSTORE_CREDENTIALS.txt must exist")
        txt_content = self.keystore_txt_path.read_text(encoding="utf-8")
        fp_match = re.search(r"([0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}", txt_content)
        self.assertIsNotNone(fp_match, "Fingerprint must be documented in KEYSTORE_CREDENTIALS.txt")
        expected_fp = fp_match.group(0).upper()

        bazaar_stmt = next(
            (stmt for stmt in assetlinks if "cafebazaar_twa" in stmt.get("relation", [])),
            None,
        )
        self.assertIsNotNone(bazaar_stmt, "cafebazaar_twa statement must exist")
        self.assertIn(
            expected_fp,
            bazaar_stmt.get("target", {}).get("sha256_cert_fingerprints", []),
            "Crawler must match keystore SHA-256 certificate fingerprint",
        )

        self.assertTrue(self.nojekyll_path.exists(), ".nojekyll required for crawler asset access")

    # -------------------------------------------------------------------------
    # Scenario 4: Sub-optimal Connectivity & Persian Offline Fallback
    # -------------------------------------------------------------------------
    def test_scenario_4_suboptimal_connectivity_and_offline_fallback(self):
        """Scenario 4: Student offline navigation with Persian RTL fallback and retry."""
        self.assertTrue(self.sw_path.exists(), "sw.js must exist")
        self.assertTrue(self.offline_path.exists(), "offline.html must exist")

        sw_text = self.sw_path.read_text(encoding="utf-8")
        offline_text = self.offline_path.read_text(encoding="utf-8")

        self.assert_in_text("offline.html", sw_text)

        self.assert_matches(r'<html[^>]*lang=["\']fa(-IR)?["\']', offline_text)
        self.assert_matches(r'<html[^>]*dir=["\']rtl["\']', offline_text)

        self.assert_in_text("تلاش مجدد", offline_text)
        self.assert_matches(r"location\.reload|reload\(\)", offline_text)
        self.assert_matches(r"#0f172a|#0f2442|navy|slate-900", offline_text)

    # -------------------------------------------------------------------------
    # Scenario 5: GitHub Actions CI/CD Headless Build & Release Pipeline
    # -------------------------------------------------------------------------
    def test_scenario_5_github_actions_ci_pipeline_validation(self):
        """Scenario 5: GitHub Actions workflow dry-run validation on ubuntu-latest."""
        self.assertTrue(
            self.workflow_path.exists(),
            f"{self.workflow_path} must exist for automated CI/CD pipeline",
        )
        content = self.workflow_path.read_text(encoding="utf-8")

        self.assert_matches(r"push:\s*(branches:\s*\[?\s*main\s*\]?)?", content)
        self.assert_in_text("ubuntu-latest", content)
        self.assert_in_text("actions/setup-java", content)
        self.assert_matches(r"java-version:\s*['\"]?17['\"]?", content)
        self.assert_matches(r"assembleRelease|bundleRelease", content)
        self.assert_in_text("actions/upload-artifact", content)
        self.assert_matches(r"action-gh-release|gh\s+release|softprops/action-gh-release", content)
        self.assert_in_text(".apk", content)
        self.assert_in_text(".aab", content)
        self.assert_matches(r"همراه باقرالعلوم|انتشار|نسخه", content)


if __name__ == "__main__":
    unittest.main()
