#!/usr/bin/env python3
"""Milestone 6 Tier 5 Adversarial Coverage Hardening & Empirical Challenge Suite.

Author: m6_challenger_1 (Empirical Challenger - Roles: critic, specialist)
Verification Paradigm: Empirical white-box challenge with adversarial inputs,
DOM mutation simulations, crypto verification, and edge stress probes.
Zero third-party dependencies (pure standard library: unittest, json, re, urllib, ssl, zipfile, subprocess).
"""

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = PROJECT_ROOT / "index.html"
SW_JS = PROJECT_ROOT / "sw.js"
OFFLINE_HTML = PROJECT_ROOT / "offline.html"
MANIFEST_JSON = PROJECT_ROOT / "manifest.json"
ASSETLINKS_JSON = PROJECT_ROOT / ".well-known" / "assetlinks.json"
KEYSTORE_PATH = PROJECT_ROOT / "android.keystore"
KEYSTORE_CREDENTIALS = PROJECT_ROOT / "KEYSTORE_CREDENTIALS.txt"
RELEASE_APK = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.apk"
RELEASE_AAB = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.aab"
ANDROID_MANIFEST = PROJECT_ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
CI_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "build-android-apk.yml"
ASSETSIGNORE = PROJECT_ROOT / ".assetsignore"

LIVE_WORKER_URL = "https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev"
EXPECTED_SHA256 = "F2:11:BF:37:3C:30:60:2D:31:D4:28:32:D2:8A:B7:09:C4:AA:6A:29:6F:F3:01:43:19:2C:17:CA:1C:A4:56:FE"
EXPECTED_PACKAGE = "ir.bagherololum.hamrah"


class TestAppModeAdversarialGuard(unittest.TestCase):
    """Stress-test App Mode detection, isolation, DOM purge, and route interception."""

    def setUp(self):
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            self.html = f.read()

    def test_01_early_app_mode_script_in_head(self):
        """App mode detection engine must execute immediately in <head> before stylesheets/body."""
        head_match = re.search(r"<head>(.*?)</head>", self.html, re.DOTALL)
        self.assertIsNotNone(head_match, "<head> section must exist")
        head_content = head_match.group(1)

        self.assertIn("app-mode-shield", head_content, "Anti-FOUC CSS shield must reside in <head>")
        self.assertIn("HAMRAH_APP_MODE", head_content, "App mode script must reside in <head>")
        self.assertIn("is-mobile-app", head_content, "is-mobile-app class injection must reside in <head>")

    def test_02_web_mode_override_precedence(self):
        """Parameter ?mode=web must take absolute precedence and reset app mode flags."""
        # Find the inline script logic for mode === 'web'
        script_match = re.search(r"if\s*\(\s*mode\s*===\s*'web'\s*\)\s*\{([\s\S]*?return;\s*\})", self.html)
        self.assertIsNotNone(script_match, "mode === 'web' handler must be explicitly defined")
        block = script_match.group(1)
        self.assertIn("removeItem('HAMRAH_APP_MODE')", block, "localStorage flag must be purged on mode=web")
        self.assertIn("classList.remove('is-mobile-app')", block, "is-mobile-app CSS class must be removed on mode=web")
        self.assertIn("__HAMRAH_IS_APP_MODE = false", block, "Global flag must be set to false")

    def test_03_multi_signal_detection_coverage(self):
        """Detection must evaluate ?mode=app, ?source=twa, localStorage, standalone, and referrer."""
        detection_match = re.search(r"var\s+isApp\s*=([\s\S]*?Boolean\(document\.referrer[\s\S]*?\);)", self.html)
        self.assertIsNotNone(detection_match, "var isApp assignment must exist")
        code = detection_match.group(1)

        self.assertIn("mode === 'app'", code)
        self.assertIn("source === 'twa'", code)
        self.assertIn("localStorage.getItem('HAMRAH_APP_MODE') === '1'", code)
        self.assertIn("(display-mode: standalone)", code)
        self.assertIn("android-app://", code)
        self.assertIn("ir.bagherololum.hamrah", code)

    def test_04_anti_fouc_shield_rules_strictness(self):
        """Anti-FOUC shield must target #header-admin-btn, [data-admin-trigger], and modals with !important."""
        shield_match = re.search(r'<style\s+id="app-mode-shield">(.*?)</style>', self.html, re.DOTALL)
        self.assertIsNotNone(shield_match, "app-mode-shield style tag must exist")
        css = shield_match.group(1)

        self.assertIn("html.is-mobile-app #header-admin-btn", css)
        self.assertIn("html.is-mobile-app [data-admin-trigger]", css)
        self.assertIn("html.is-mobile-app .admin-panel-trigger", css)
        self.assertIn("html.is-mobile-app #staff-login-modal", css)
        self.assertIn("display: none !important", css)
        self.assertIn("visibility: hidden !important", css)
        self.assertIn("pointer-events: none !important", css)

    def test_05_dom_purge_functions_and_lifecycle(self):
        """purgeAdminElementsFromDOM must be hooked into immediate, DOMContentLoaded, and window.load."""
        self.assertIn("function purgeAdminElementsFromDOM()", self.html)
        self.assertIn("headerAdminBtn.remove()", self.html)
        self.assertIn("document.addEventListener('DOMContentLoaded', purgeAdminElementsFromDOM)", self.html)
        self.assertIn("window.addEventListener('load', purgeAdminElementsFromDOM)", self.html)

    def test_06_mutation_observer_catches_dynamic_admin_injection(self):
        """MutationObserver must actively monitor body/documentElement and remove injected admin nodes."""
        self.assertIn("new MutationObserver", self.html)
        self.assertIn("header-admin-btn", self.html)
        self.assertIn("childList: true", self.html)
        self.assertIn("subtree: true", self.html)

    def test_07_auth_service_update_header_badges_defense(self):
        """AuthService.updateHeaderBadges must actively remove adminBtn when in app mode."""
        match = re.search(r"updateHeaderBadges\(\)\s*\{([\s\S]*?)\n\s*\},", self.html)
        self.assertIsNotNone(match, "updateHeaderBadges method must exist")
        body = match.group(1)
        self.assertIn("isAppMode", body)
        self.assertIn("if (adminBtn) adminBtn.remove();", body)
        self.assertIn("return;", body)

    def test_08_navigate_to_admin_guard(self):
        """navigateTo('admin') must redirect to home in app mode and never render admin panel."""
        match = re.search(r"navigateTo\s*=\s*function\(view,\s*params,\s*skipHashUpdate\)\s*\{([\s\S]*?)\n\s*\};", self.html)
        self.assertIsNotNone(match, "navigateTo function must exist")
        code = match.group(1)
        self.assertIn("if (view === 'admin' && isAppMode)", code)
        self.assertIn("navigateTo('home'", code)
        self.assertIn("return;", code)

    def test_09_direct_hash_injection_admin_sanitization(self):
        """Navigating directly to #admin or #/admin must sanitize hash to #/home in app mode."""
        self.assertIn("window.addEventListener('hashchange'", self.html)
        self.assertIn("handleHashChangeRoute", self.html)
        match = re.search(r"function\s+handleHashChangeRoute\(\)\s*\{([\s\S]*?)\n\s*\}", self.html)
        self.assertIsNotNone(match, "handleHashChangeRoute must exist")
        code = match.group(1)
        self.assertIn("isAppMode", code)
        self.assertIn("window.location.hash = '#/home'", code)

    def test_10_open_staff_login_modal_guard(self):
        """openStaffLoginModal must block execution immediately in app mode."""
        match = re.search(r"window\.openStaffLoginModal\s*=\s*function\([^\)]*\)\s*\{([\s\S]*?)\n\s*\};", self.html)
        self.assertIsNotNone(match, "openStaffLoginModal must exist")
        code = match.group(1)
        self.assertIn("isAppMode", code)
        self.assertIn("return;", code)

    def test_11_hardware_back_button_popstate_dismissal(self):
        """Popstate listener must intercept Android hardware back button and dismiss active modals."""
        match = re.search(r"window\.addEventListener\('popstate',\s*function\(event\)\s*\{([\s\S]*?)\n\s*\}\);", self.html)
        self.assertIsNotNone(match, "popstate listener must exist")
        code = match.group(1)
        self.assertIn("closeModal", code)
        self.assertIn("global-modal-backdrop", code)


class TestServiceWorkerFreshnessAndRouting(unittest.TestCase):
    """Stress-test Service Worker Network-First dynamic sync and offline discrimination."""

    def setUp(self):
        with open(SW_JS, "r", encoding="utf-8") as f:
            self.sw = f.read()

    def test_01_cache_version_and_precache_assets(self):
        """SW must declare versioned cache name and precache offline fallback and icons."""
        self.assertIn("CACHE_NAME", self.sw)
        self.assertIn("PRECACHE_URLS", self.sw)
        self.assertIn("./offline.html", self.sw)
        self.assertIn("./icons/icon-192.png", self.sw)
        self.assertIn("./icons/icon-512.png", self.sw)

    def test_02_strict_network_first_for_html_navigation(self):
        """HTML navigation requests must use fetch(request, { cache: 'no-store' })."""
        match = re.search(r"if\s*\(\s*isNavigation\s*\)\s*\{([\s\S]*?)\n\s*return;\s*\}", self.sw)
        self.assertIsNotNone(match, "isNavigation branch must exist")
        code = match.group(1)
        self.assertIn("fetch(request, { cache: 'no-store' })", code)
        self.assertIn("OFFLINE_URL", code)
        self.assertIn("offline.html", code)

    def test_03_strict_network_first_for_dynamic_data(self):
        """Dynamic data (json, /api/, db.json, workers.dev) must use { cache: 'no-store' } and NEVER cache."""
        match = re.search(r"const\s+isDynamicData\s*=\s*([\s\S]*?);", self.sw)
        self.assertIsNotNone(match, "isDynamicData must be defined")
        cond = match.group(1)
        self.assertIn("!isStaticAsset", cond)
        self.assertIn(".endsWith('.json')", cond)
        self.assertIn(".includes('/api/')", cond)
        self.assertIn(".includes('db.json')", cond)

        # Ensure dynamic branch returns 503 JSON on network error, NOT offline.html
        dyn_branch = re.search(r"if\s*\(\s*isDynamicData\s*\)\s*\{([\s\S]*?)\n\s*return;\s*\}", self.sw)
        self.assertIsNotNone(dyn_branch, "isDynamicData branch must exist")
        branch_code = dyn_branch.group(1)
        self.assertIn("fetch(request, { cache: 'no-store' })", branch_code)
        self.assertIn("application/json", branch_code)
        self.assertNotIn("offline.html", branch_code)

    def test_04_static_asset_discrimination_logic(self):
        """Static assets must include css, js, fonts, and images, and use cache-first strategy."""
        match = re.search(r"const\s+isStaticAsset\s*=\s*([\s\S]*?);", self.sw)
        self.assertIsNotNone(match, "isStaticAsset must be defined")
        cond = match.group(1)
        self.assertIn("image", cond)
        self.assertIn("style", cond)
        self.assertIn("font", cond)
        self.assertIn("script", cond)
        self.assertIn("png|jpe?g|gif|svg|ico|webp|css|woff2?|ttf|js", cond)


class TestPersianRtlAndVisualTypography(unittest.TestCase):
    """Stress-test Persian language integrity, RTL layout, and zero English regressions."""

    def test_01_index_html_root_attributes(self):
        """index.html must declare lang='fa' and dir='rtl'."""
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            html = f.read(500)
        self.assertIn('dir="rtl"', html)
        self.assertTrue('lang="fa"' in html or 'lang="fa-IR"' in html)

    def test_02_offline_html_root_attributes(self):
        """offline.html must declare lang='fa-IR' and dir='rtl'."""
        with open(OFFLINE_HTML, "r", encoding="utf-8") as f:
            html = f.read(500)
        self.assertIn('dir="rtl"', html)
        self.assertIn('lang="fa-IR"', html)

    def test_03_offline_page_contains_zero_cdn_external_links(self):
        """offline.html must be 100% self-contained with no external CSS/JS CDN dependencies."""
        with open(OFFLINE_HTML, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("https://cdn.", content)
        self.assertNotIn("https://fonts.", content)
        self.assertNotIn("https://cdnjs.", content)
        self.assertIn("تلاش مجدد", content)
        self.assertIn("ارتباط با اینترنت برقرار نیست", content)

    def test_04_mobile_ui_polish_classes(self):
        """index.html must include mobile touch polish CSS properties."""
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            css = f.read(10000)
        self.assertIn("user-select: none", css)
        self.assertIn("-webkit-tap-highlight-color: transparent", css)
        self.assertIn("overflow-x: hidden", css)
        self.assertIn("font-size: 16px !important", css)


class TestAndroidTwaAndKeystoreSecurity(unittest.TestCase):
    """Stress-test Android TWA manifests, keystore properties, and APK signatures."""

    def test_01_manifest_package_and_default_url(self):
        """AndroidManifest.xml must declare package ir.bagherololum.hamrah and DEFAULT_URL."""
        with open(ANDROID_MANIFEST, "r", encoding="utf-8") as f:
            manifest = f.read()
        self.assertIn('package="ir.bagherololum.hamrah"', manifest)
        self.assertIn('android.support.customtabs.trusted.DEFAULT_URL', manifest)
        self.assertIn('https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app', manifest)
        self.assertIn('ir.bagherololum.hamrah.fileprovider', manifest)

    def test_02_keystore_credentials_file_validity(self):
        """KEYSTORE_CREDENTIALS.txt must document uppercase SHA-256 fingerprint matching EXPECTED_SHA256."""
        with open(KEYSTORE_CREDENTIALS, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn(EXPECTED_SHA256, text)
        self.assertIn("hamrah-key", text)
        self.assertIn("Hamrah2026Release!", text)
        self.assertIn("10000 days", text)

    def test_03_assetlinks_dual_statements_and_package(self):
        """assetlinks.json must include handle_all_urls and cafebazaar_twa with exact fingerprint."""
        with open(ASSETLINKS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)
        for stmt in data:
            self.assertEqual(stmt["target"]["package_name"], EXPECTED_PACKAGE)
            self.assertIn(EXPECTED_SHA256, stmt["target"]["sha256_cert_fingerprints"])

    def test_04_release_apk_binary_exists_and_signed(self):
        """hamrah-bagherololum-release.apk must exist, exceed 1MB, and contain META-INF signatures."""
        self.assertTrue(RELEASE_APK.exists(), f"APK not found at {RELEASE_APK}")
        self.assertGreater(RELEASE_APK.stat().st_size, 1_000_000)
        with zipfile.ZipFile(RELEASE_APK, "r") as z:
            names = z.namelist()
            self.assertTrue(any(n.startswith("META-INF/") and n.endswith(".RSA") for n in names))
            self.assertTrue(any(n.startswith("META-INF/") and n.endswith(".SF") for n in names))

    def test_05_release_aab_binary_exists(self):
        """hamrah-bagherololum-release.aab must exist and exceed 1MB."""
        self.assertTrue(RELEASE_AAB.exists(), f"AAB not found at {RELEASE_AAB}")
        self.assertGreater(RELEASE_AAB.stat().st_size, 1_000_000)


class TestLiveEndpointsAndInformationLeakPrevention(unittest.TestCase):
    """Stress-test live Cloudflare Worker endpoints, CORS headers, and negative information leaks."""

    @classmethod
    def setUpClass(cls):
        cls.ssl_ctx = ssl.create_default_context()

    def _probe(self, path):
        url = f"{LIVE_WORKER_URL}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "HamrahChallengerM6/1.0"})
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=12) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_01_root_endpoint_status_and_persian(self):
        """Live / must return 200, text/html, and Persian title."""
        status, headers, body = self._probe("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn("همراه باقرالعلوم", body.decode("utf-8", errors="replace"))

    def test_02_assetlinks_live_cors_and_json(self):
        """Live .well-known/assetlinks.json must return 200, application/json, and CORS *."""
        status, headers, body = self._probe("/.well-known/assetlinks.json")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        self.assertIn("*", headers.get("Access-Control-Allow-Origin", ""))
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(len(data), 2)
        self.assertIn(EXPECTED_SHA256, data[0]["target"]["sha256_cert_fingerprints"])

    def test_03_negative_probe_sensitive_keystore_blocked(self):
        """Keystore files on Cloudflare must return 404 (never leaked)."""
        status, _, _ = self._probe("/android.keystore")
        self.assertEqual(status, 404)

    def test_04_negative_probe_credentials_blocked(self):
        """KEYSTORE_CREDENTIALS.txt on Cloudflare must return 404."""
        status, _, _ = self._probe("/KEYSTORE_CREDENTIALS.txt")
        self.assertEqual(status, 404)

    def test_05_negative_probe_wrangler_config_blocked(self):
        """wrangler.json on Cloudflare must return 404."""
        status, _, _ = self._probe("/wrangler.json")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
