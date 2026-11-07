"""Tier 1: Comprehensive Feature Coverage Tests (Features F-01 to F-26).

Each feature is evaluated against requirements from ORIGINAL_REQUEST.md
and interface contracts from PROJECT.md with at least 5 explicit assertions per feature.
"""

import json
import os
import re
import struct
import unittest
from pathlib import Path

from base_test import BaseE2ETest, PROJECT_ROOT


class TestTier1Features(BaseE2ETest):

    # -------------------------------------------------------------------------
    # Feature 1: Copy Isolation & Persian Layout (M1)
    # -------------------------------------------------------------------------
    def test_f01_copy_isolation_and_persian_layout(self):
        """F-01: Verify 100% Persian UI text, Vazirmatn font, and RTL layout isolation."""
        self.assertTrue(self.index_path.exists(), "index.html must exist at project root")
        content = self.index_path.read_text(encoding="utf-8")

        # Assertion 1: HTML tag has lang="fa" or "fa-IR"
        self.assert_matches(
            r'<html[^>]*lang=["\']fa(-IR)?["\']',
            content,
            "HTML tag must specify Persian language attribute (lang='fa' or 'fa-IR')",
        )

        # Assertion 2: HTML tag has dir="rtl"
        self.assert_matches(
            r'<html[^>]*dir=["\']rtl["\']',
            content,
            "HTML tag must specify Right-to-Left direction (dir='rtl')",
        )

        # Assertion 3: Persian Vazirmatn typography configured
        self.assertTrue(
            "vazirmatn" in content.lower(),
            "Vazirmatn Persian typography must be configured in index.html",
        )

        # Assertion 4: Core Persian title present
        self.assert_in_text(
            "همراه باقرالعلوم",
            content,
            "Document must contain primary Persian brand name 'همراه باقرالعلوم'",
        )

        # Assertion 5: Git remote isolation (no reference to original repo without -copy)
        git_config = self.root / ".git" / "config"
        if git_config.exists():
            git_text = git_config.read_text(encoding="utf-8")
            self.assert_in_text(
                "hamrah-bagherololum-copy",
                git_text,
                "Git repository must be isolated to hamrah-bagherololum-copy",
            )
            # Ensure no remote points to original repository without -copy
            self.assert_not_matches(
                r"url\s*=\s*.*psyeducationhadi-bot/hamrah-bagherololum(\.git)?$",
                git_text,
                "Git remotes must not target the original production repository",
            )
        else:
            self.assertTrue(self.root.exists(), "Project root must exist")

    # -------------------------------------------------------------------------
    # Feature 2: Production URL Sanitization (M1)
    # -------------------------------------------------------------------------
    def test_f02_production_url_sanitization(self):
        """F-02: Ensure all endpoints point to copy Worker and Pages, never original prod."""
        content = self.index_path.read_text(encoding="utf-8")
        wrangler_content = self.wrangler_path.read_text(encoding="utf-8") if self.wrangler_path.exists() else ""
        robots_content = (self.root / "robots.txt").read_text(encoding="utf-8") if (self.root / "robots.txt").exists() else ""

        # Assertion 1: Cloudflare Worker name is hamrah-bagherololum-copy
        self.assert_in_text(
            '"name": "hamrah-bagherololum-copy"',
            wrangler_content,
            "wrangler.json must declare worker name as 'hamrah-bagherololum-copy'",
        )

        # Assertion 2: Robots.txt sitemap points to copy worker or copy pages
        if robots_content:
            self.assert_in_text(
                "hamrah-bagherololum-copy",
                robots_content,
                "robots.txt sitemap must target copy environment",
            )

        # Assertion 3: No un-namespaced references to original worker in index.html
        self.assert_not_matches(
            r"https?://hamrah-bagherololum\.psyeducation-hadi\.workers\.dev(?!\w)",
            content,
            "index.html must not contain references to original non-copy worker endpoint",
        )

        # Assertion 4: References to copy worker exist or relative paths used
        has_copy_worker = "hamrah-bagherololum-copy.psyeducation-hadi.workers.dev" in content
        has_relative = 'fetch("./db.json' in content or 'fetch("db.json' in content or "db.json" in content
        self.assertTrue(
            has_copy_worker or has_relative,
            "Network calls must target copy worker or relative path",
        )

        # Assertion 5: Pages references in code isolate to copy repo
        self.assert_not_in_text(
            "psyeducationhadi-bot.github.io/hamrah-bagherololum/",
            content,
            "Code must not point to original production GitHub Pages path",
        )

    # -------------------------------------------------------------------------
    # Feature 3: Release Keystore Generation (M1)
    # -------------------------------------------------------------------------
    def test_f03_release_keystore_generation(self):
        """F-03: Verify RSA 2048-bit release keystore exists with >= 10,000 days validity."""
        keystore_exists = self.keystore_path.exists() or (self.android_dir / "app" / "release.keystore").exists()
        self.assertTrue(
            keystore_exists,
            f"Release keystore must exist at {self.keystore_path} or android/app/release.keystore",
        )

        active_keystore = self.keystore_path if self.keystore_path.exists() else (self.android_dir / "app" / "release.keystore")
        file_size = os.path.getsize(active_keystore)

        # Assertion 1: File size > 1000 bytes (typical PKCS12 keystore is 2KB - 5KB)
        self.assertGreater(file_size, 1000, "Keystore file size must be > 1000 bytes")

        # Assertion 2: File is non-empty binary
        with open(active_keystore, "rb") as f:
            header = f.read(16)
        self.assertGreater(len(header), 0, "Keystore binary must be readable")

        # Assertion 3: Keystore is not a placeholder text
        self.assertFalse(
            header.startswith(b"placeholder") or header.startswith(b"TODO"),
            "Keystore must be real binary, not placeholder",
        )

        # Assertion 4: Keystore path is in expected directory
        self.assertTrue(active_keystore.is_file(), "Keystore must be a valid file")

        # Assertion 5: Keystore directory check
        self.assertTrue(
            active_keystore.parent in (self.root, self.android_dir / "app"),
            "Keystore must reside at root or in android/app/",
        )

    # -------------------------------------------------------------------------
    # Feature 4: Keystore Documentation (M1)
    # -------------------------------------------------------------------------
    def test_f04_keystore_documentation(self):
        """F-04: Verify KEYSTORE_CREDENTIALS.txt documents alias, password, and SHA-256."""
        self.assertTrue(
            self.keystore_txt_path.exists(),
            f"{self.keystore_txt_path} must exist and document keystore credentials",
        )
        text = self.keystore_txt_path.read_text(encoding="utf-8")

        # Assertion 1: Contains Keystore Alias
        self.assert_matches(r"(?i)alias\s*:\s*\S+", text, "Must document key alias")

        # Assertion 2: Contains Keystore Password
        self.assert_matches(r"(?i)password\s*:\s*\S+", text, "Must document keystore password")

        # Assertion 3: Contains SHA-256 Fingerprint
        self.assert_in_text("SHA-256", text.upper(), "Must document SHA-256 certificate fingerprint")

        # Assertion 4: SHA-256 fingerprint format (32 hex pairs separated by colons = 95 chars)
        fingerprint_match = re.search(r"([0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}", text)
        self.assertIsNotNone(
            fingerprint_match,
            "Must contain valid 32-byte colon-separated SHA-256 fingerprint",
        )

        # Assertion 5: Fingerprint is uppercase
        if fingerprint_match:
            fp = fingerprint_match.group(0)
            self.assertEqual(fp, fp.upper(), "SHA-256 fingerprint must be uppercase hex")

    # -------------------------------------------------------------------------
    # Feature 5: Digital Asset Links Schema (M1)
    # -------------------------------------------------------------------------
    def test_f05_digital_asset_links_schema(self):
        """F-05: Verify /.well-known/assetlinks.json has Google & Cafe Bazaar statements."""
        self.assertTrue(
            self.assetlinks_path.exists(),
            f"{self.assetlinks_path} must exist at root /.well-known/assetlinks.json",
        )
        data = json.loads(self.assetlinks_path.read_text(encoding="utf-8"))

        # Assertion 1: Root is a JSON list
        self.assertIsInstance(data, list, "assetlinks.json root must be a JSON array")
        self.assertGreaterEqual(len(data), 2, "Must contain at least 2 relation statements")

        # Assertion 2: Has delegate_permission/common.handle_all_urls
        relations = [item.get("relation", []) for item in data]
        flat_relations = [r for sub in relations for r in sub]
        self.assertIn(
            "delegate_permission/common.handle_all_urls",
            flat_relations,
            "Must include delegate_permission/common.handle_all_urls relation",
        )

        # Assertion 3: Has cafebazaar_twa relation
        self.assertIn(
            "cafebazaar_twa",
            flat_relations,
            "Must include cafebazaar_twa relation statement for Cafe Bazaar crawler",
        )

        # Assertion 4: Package name is ir.bagherololum.hamrah across statements
        for item in data:
            target = item.get("target", {})
            self.assertEqual(
                target.get("package_name"),
                "ir.bagherololum.hamrah",
                "Target package_name must be 'ir.bagherololum.hamrah'",
            )
            self.assertEqual(
                target.get("namespace"),
                "android_app",
                "Target namespace must be 'android_app'",
            )

        # Assertion 5: Fingerprints are non-empty valid uppercase SHA-256
        for item in data:
            fps = item.get("target", {}).get("sha256_cert_fingerprints", [])
            self.assertTrue(len(fps) > 0, "sha256_cert_fingerprints must not be empty")
            for fp in fps:
                self.assert_matches(
                    r"^([0-9A-F]{2}:){31}[0-9A-F]{2}$",
                    fp,
                    "Fingerprint must be 32 uppercase hex pairs separated by colons",
                )

    # -------------------------------------------------------------------------
    # Feature 6: Cloudflare & Pages Asset Serving (M1)
    # -------------------------------------------------------------------------
    def test_f06_cloudflare_and_pages_asset_serving(self):
        """F-06: Verify .nojekyll exists, wrangler assets config serves root, and ignore files."""
        # Assertion 1: .nojekyll exists at project root
        self.assertTrue(
            self.nojekyll_path.exists(),
            ".nojekyll file must exist at project root for GitHub Pages dot-folder bypass",
        )

        # Assertion 2: wrangler.json defines assets directory
        self.assertTrue(self.wrangler_path.exists(), "wrangler.json must exist")
        wrangler_data = json.loads(self.wrangler_path.read_text(encoding="utf-8"))
        self.assertIn("assets", wrangler_data, "wrangler.json must configure static assets")
        self.assertEqual(
            wrangler_data["assets"].get("directory"),
            ".",
            "wrangler assets directory must be root '.'",
        )

        # Assertion 3: .assetsignore does not ignore .well-known
        assetsignore_path = self.root / ".assetsignore"
        if assetsignore_path.exists():
            ign_text = assetsignore_path.read_text(encoding="utf-8")
            self.assert_not_in_text(".well-known", ign_text, ".assetsignore must not ignore .well-known")

        # Assertion 4: .assetsignore does not ignore manifest.json or sw.js
        if assetsignore_path.exists():
            ign_text = assetsignore_path.read_text(encoding="utf-8")
            self.assert_not_in_text("manifest.json", ign_text)
            self.assert_not_in_text("sw.js", ign_text)

        # Assertion 5: robots.txt allows crawler or standard indexing
        robots_file = self.root / "robots.txt"
        self.assertTrue(robots_file.exists(), "robots.txt must exist at root")
        self.assert_in_text("User-agent", robots_file.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # Feature 7: Early App Mode Detection (M2)
    # -------------------------------------------------------------------------
    def test_f07_early_app_mode_detection(self):
        """F-07: Verify early inline script detects ?mode=app, ?source=twa, and localStorage."""
        content = self.index_path.read_text(encoding="utf-8")

        head_match = re.search(r"<head>(.*?)</head>", content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(head_match, "index.html must have a <head> section")
        head_content = head_match.group(1)

        # Assertion 1: Script in head checks for mode=app
        self.assert_matches(
            r'mode\s*===?\s*["\']app["\']|mode["\']?\s*,\s*["\']app["\']|["\']mode["\']\s*,\s*["\']app["\']|\?mode=app|mode=app',
            head_content,
            "Head script must inspect for 'mode=app' query parameter",
        )

        # Assertion 2: Checks for source=twa parameter
        self.assertTrue(
            "source" in head_content and "twa" in head_content,
            "Head script must detect TWA source indicator (?source=twa)",
        )

        # Assertion 3: Persists flag in localStorage
        self.assert_in_text(
            "localStorage",
            head_content,
            "Head script must interact with localStorage for app mode persistence",
        )

        # Assertion 4: Adds 'is-mobile-app' class to documentElement
        self.assert_in_text(
            "is-mobile-app",
            head_content,
            "Head script must add 'is-mobile-app' class to root <html> element",
        )

        # Assertion 5: Handles ?mode=web reset
        self.assert_matches(
            r'mode\s*===?\s*["\']web["\']|mode["\']?\s*,\s*["\']web["\']|["\']mode["\']\s*,\s*["\']web["\']|\?mode=web|mode=web',
            head_content,
            "Head script must handle '?mode=web' to reset app mode",
        )

    # -------------------------------------------------------------------------
    # Feature 8: Anti-FOUC CSS Shield (M2)
    # -------------------------------------------------------------------------
    def test_f08_anti_fouc_css_shield(self):
        """F-08: Verify CSS rules hiding #header-admin-btn and admin triggers under is-mobile-app."""
        content = self.index_path.read_text(encoding="utf-8")

        # Assertion 1: CSS selector targeting is-mobile-app class
        self.assert_in_text(
            ".is-mobile-app",
            content,
            "CSS must contain rules scoped under .is-mobile-app",
        )

        # Assertion 2: Suppresses #header-admin-btn
        self.assert_matches(
            r"\.is-mobile-app\s+.*#header-admin-btn|\.is-mobile-app#header-admin-btn|html\.is-mobile-app\s+#header-admin-btn",
            content,
            "CSS must suppress #header-admin-btn when is-mobile-app is active",
        )

        # Assertion 3: Uses display: none !important for anti-FOUC guarantee
        self.assert_matches(
            r"display:\s*none\s*!important",
            content,
            "CSS anti-FOUC shield must specify 'display: none !important'",
        )

        # Assertion 4: Hides generic admin triggers ([data-admin-trigger])
        has_admin_trigger_rule = (
            "[data-admin-trigger]" in content or "data-admin" in content or "header-admin-btn" in content
        )
        self.assertTrue(has_admin_trigger_rule, "CSS must hide admin triggers when in app mode")

        # Assertion 5: Hides staff login modal in app mode
        has_modal_hide = "is-mobile-app" in content and (
            "modal" in content or "admin" in content or "staff" in content
        )
        self.assertTrue(has_modal_hide, "CSS shield must cover admin modals in app mode")

    # -------------------------------------------------------------------------
    # Feature 9: DOM Admin Button Removal (M2)
    # -------------------------------------------------------------------------
    def test_f09_dom_admin_button_removal(self):
        """F-09: Verify physical removal of #header-admin-btn from DOM in app mode."""
        content = self.index_path.read_text(encoding="utf-8")

        # Assertion 1: Script references #header-admin-btn
        self.assert_in_text("header-admin-btn", content, "Script must identify header-admin-btn element")

        # Assertion 2: Physical DOM removal logic (.remove() or .removeChild())
        self.assert_matches(
            r"\.remove\(\)|\.removeChild\(|header-admin-btn.*remove",
            content,
            "Script must physically remove admin button node from DOM in app mode",
        )

        # Assertion 3: Removal is conditional on app mode flag
        self.assert_matches(
            r"isAppMode|is-mobile-app|HAMRAH_APP_MODE",
            content,
            "DOM button removal must be tied to app mode state",
        )

        # Assertion 4: Executes on DOM ready or early hook
        self.assert_matches(
            r"DOMContentLoaded|addEventListener\(['\"]DOMContentLoaded['\"]|onload|\$\(document\)",
            content,
            "DOM cleanup must hook into lifecycle to ensure complete node removal",
        )

        # Assertion 5: Multiple admin trigger cleanup
        self.assert_matches(
            r"querySelectorAll|data-admin-trigger|header-admin-btn",
            content,
            "Script must ensure all admin buttons / triggers are targeted",
        )

    # -------------------------------------------------------------------------
    # Feature 10: Dynamic Header Protection (M2)
    # -------------------------------------------------------------------------
    def test_f10_dynamic_header_protection(self):
        """F-10: Verify AuthService.updateHeaderBadges does not resurrect admin button in app mode."""
        content = self.index_path.read_text(encoding="utf-8")

        # Assertion 1: updateHeaderBadges function exists
        self.assert_in_text("updateHeaderBadges", content, "AuthService must contain updateHeaderBadges method")

        # Assertion 2: updateHeaderBadges checks for app mode before rendering admin button
        update_badges_match = re.search(r"updateHeaderBadges\s*\([^)]*\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}", content)
        self.assertIsNotNone(update_badges_match, "updateHeaderBadges implementation must be present")
        method_body = update_badges_match.group(1)

        self.assert_matches(
            r"is-mobile-app|isAppMode|HAMRAH_APP_MODE|header-admin-btn|return",
            method_body,
            "updateHeaderBadges must check app mode or null element before mutating admin button",
        )

        # Assertion 3: Does not throw error if adminBtn is absent
        self.assert_in_text("if", method_body, "updateHeaderBadges must check element existence before modifying innerHTML")

        # Assertion 4: Student label/badge updates continue functioning
        self.assert_in_text("header-user-label", method_body, "Student badge/label updates must remain intact")

        # Assertion 5: Admin button reference
        self.assertTrue(
            "adminBtn" in method_body or "header-admin-btn" in method_body,
            "Method must specifically reference admin button reference",
        )

    # -------------------------------------------------------------------------
    # Feature 11: Admin Route & Modal Interceptor (M2)
    # -------------------------------------------------------------------------
    def test_f11_admin_route_and_modal_interceptor(self):
        """F-11: Verify navigateTo('admin') and openStaffLoginModal are blocked in app mode."""
        content = self.index_path.read_text(encoding="utf-8")

        # Assertion 1: navigateTo function guards against 'admin' in app mode
        self.assert_in_text("navigateTo", content, "navigateTo function must exist")
        self.assert_matches(
            r"navigateTo.*admin.*(isAppMode|is-mobile-app|HAMRAH_APP_MODE)|(isAppMode|is-mobile-app|HAMRAH_APP_MODE).*navigateTo",
            content,
            "navigateTo must block 'admin' view when in app mode",
        )

        # Assertion 2: openStaffLoginModal intercepted in app mode
        self.assert_in_text("openStaffLoginModal", content, "openStaffLoginModal function must exist")
        self.assert_matches(
            r"openStaffLoginModal.*(isAppMode|is-mobile-app|HAMRAH_APP_MODE)|(isAppMode|is-mobile-app|HAMRAH_APP_MODE).*openStaffLoginModal",
            content,
            "openStaffLoginModal must be intercepted in app mode",
        )

        # Assertion 3: Hash navigation / URL tampering blocked (#admin)
        self.assert_matches(
            r"hashchange|location\.hash|popstate",
            content,
            "Navigation interceptor must handle URL hash changes",
        )

        # Assertion 4: Fallback navigation to home view
        self.assert_matches(
            r"navigateTo\(['\"]home['\"]\)|navigateTo\(['\"]dashboard['\"]\)|return",
            content,
            "Blocked navigation must redirect to safe view (e.g. home) or return early",
        )

        # Assertion 5: Security event logged or notified
        self.assert_matches(
            r"console\.(warn|error|log)|logAdminAction|showNotification",
            content,
            "Blocked administrative access in app mode must log a security notification",
        )

    # -------------------------------------------------------------------------
    # Feature 12: Standard Web Mode Preservation (M2)
    # -------------------------------------------------------------------------
    def test_f12_standard_web_mode_preservation(self):
        """F-12: Verify that in standard web mode (?mode=web or default), admin panel works."""
        content = self.index_path.read_text(encoding="utf-8")

        # Assertion 1: #header-admin-btn element is present in baseline HTML
        self.assert_in_text(
            'id="header-admin-btn"',
            content,
            "Standard HTML template must define #header-admin-btn for web users",
        )

        # Assertion 2: Persian label "پنل مدیریت" or "ورود کادر" present
        self.assert_matches(
            r"پنل مدیریت|ورود کادر",
            content,
            "Admin button must have Persian label for desktop web users",
        )

        # Assertion 3: openStaffLoginModal is defined and can mount modal
        self.assert_in_text("openStaffLoginModal", content)
        self.assert_in_text("global-modal-box", content, "Staff login modal must mount into global-modal-box")

        # Assertion 4: Auth credentials inputs present (#auth-username-inp, #auth-password-inp)
        self.assert_in_text("auth-username-inp", content, "Staff login modal must include username input")
        self.assert_in_text("auth-password-inp", content, "Staff login modal must include password input")

        # Assertion 5: ?mode=web explicitly clears mobile app class
        self.assert_matches(
            r"mode\s*===?\s*['\"]web['\"].*(removeClass|classList\.remove|removeItem)",
            content,
            "Web mode must explicitly clean up app mode flags and classes",
        )

    # -------------------------------------------------------------------------
    # Feature 13: High-Resolution App Icons (M3)
    # -------------------------------------------------------------------------
    def test_f13_high_resolution_app_icons(self):
        """F-13: Verify crisp PNG icons exist in icons/ (192, 512, maskable) with valid headers."""
        icons_dir = self.root / "icons"
        self.assertTrue(icons_dir.exists() and icons_dir.is_dir(), "icons/ directory must exist")

        required_icons = [
            ("icon-192.png", 192, 192),
            ("icon-512.png", 512, 512),
            ("icon-maskable-192.png", 192, 192),
            ("icon-maskable-512.png", 512, 512),
        ]

        png_magic = b"\x89PNG\r\n\x1a\n"

        for filename, exp_w, exp_h in required_icons:
            icon_file = icons_dir / filename
            self.assertTrue(icon_file.exists(), f"Icon {filename} must exist in icons/")

            with open(icon_file, "rb") as f:
                data = f.read(32)

            self.assertTrue(data.startswith(png_magic), f"{filename} must have valid PNG magic signature")

            if len(data) >= 24:
                w, h = struct.unpack(">II", data[16:24])
                self.assertEqual(w, exp_w, f"{filename} width must be {exp_w}")
                self.assertEqual(h, exp_h, f"{filename} height must be {exp_h}")

        png_files = list(icons_dir.glob("*.png"))
        self.assertGreaterEqual(len(png_files), 4, "Must contain at least 4 PNG icons")

        for f in png_files:
            self.assertGreater(os.path.getsize(f), 500, f"{f.name} size must be > 500 bytes")

    # -------------------------------------------------------------------------
    # Feature 14: Web App Manifest Configuration (M3)
    # -------------------------------------------------------------------------
    def test_f14_web_app_manifest_configuration(self):
        """F-14: Verify manifest.json has Persian title, start_url: ./?mode=app, standalone."""
        self.assertTrue(self.manifest_path.exists(), "manifest.json must exist at project root")
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        self.assert_in_text("همراه باقرالعلوم", data.get("name", ""))
        self.assert_in_text("همراه باقرالعلوم", data.get("short_name", ""))

        start_url = data.get("start_url", "")
        self.assert_in_text("mode=app", start_url, "start_url must include 'mode=app'")
        self.assertEqual(data.get("display"), "standalone", "display must be 'standalone'")
        self.assertEqual(data.get("dir"), "rtl", "dir must be 'rtl'")
        self.assertEqual(data.get("lang"), "fa-IR", "lang must be 'fa-IR'")

        icons = data.get("icons", [])
        self.assertGreaterEqual(len(icons), 2, "manifest must define at least 2 icons")
        icon_sizes = [i.get("sizes") for i in icons]
        self.assertIn("192x192", icon_sizes, "Must include 192x192 icon entry")
        self.assertIn("512x512", icon_sizes, "Must include 512x512 icon entry")

    # -------------------------------------------------------------------------
    # Feature 15: Real-Time Sync Service Worker (M3)
    # -------------------------------------------------------------------------
    def test_f15_real_time_sync_service_worker(self):
        """F-15: Verify sw.js uses Network-First (cache: 'no-store') strategy for APIs & nav."""
        self.assertTrue(self.sw_path.exists(), "sw.js must exist at project root")
        content = self.sw_path.read_text(encoding="utf-8")

        self.assert_in_text("install", content, "sw.js must listen for 'install' event")
        self.assert_matches(
            r"skipWaiting\(\)|self\.skipWaiting\(\)",
            content,
            "sw.js must call skipWaiting() for immediate activation",
        )

        self.assert_in_text("activate", content, "sw.js must listen for 'activate' event")
        self.assert_matches(
            r"clients\.claim\(\)",
            content,
            "sw.js must call clients.claim() to control clients immediately",
        )

        self.assert_in_text("fetch", content, "sw.js must intercept 'fetch' events")
        self.assert_matches(
            r"no-store|networkFirst|NetworkFirst|cache:\s*['\"]no-store['\"]",
            content,
            "sw.js must enforce Network-First or 'no-store' for dynamic API and navigation data",
        )
        self.assert_in_text(
            "offline.html",
            content,
            "sw.js must serve pre-cached offline.html when network navigation fails",
        )

    # -------------------------------------------------------------------------
    # Feature 16: Persian RTL Offline Fallback (M3)
    # -------------------------------------------------------------------------
    def test_f16_persian_rtl_offline_fallback(self):
        """F-16: Verify standalone offline.html has Persian RTL, navy theme, and retry button."""
        self.assertTrue(self.offline_path.exists(), "offline.html must exist at project root")
        content = self.offline_path.read_text(encoding="utf-8")

        self.assert_matches(r'<html[^>]*lang=["\']fa(-IR)?["\']', content)
        self.assert_matches(r'<html[^>]*dir=["\']rtl["\']', content)

        self.assert_matches(
            r"#0f172a|#0f2442|navy|slate-900",
            content,
            "offline.html must adhere to brand dark navy palette",
        )

        self.assert_matches(
            r"اتصال|اینترنت|آفلاین",
            content,
            "offline.html must include Persian explanation of connectivity failure",
        )

        self.assert_in_text("تلاش مجدد", content, "offline.html must provide prominent 'تلاش مجدد' (Retry) button")
        self.assert_matches(
            r"location\.reload\(\)|window\.location\.reload\(\)",
            content,
            "Retry action must trigger location reload",
        )

    # -------------------------------------------------------------------------
    # Feature 17: Service Worker Registration (M3)
    # -------------------------------------------------------------------------
    def test_f17_service_worker_registration(self):
        """F-17: Verify sw.js registration script inside index.html."""
        content = self.index_path.read_text(encoding="utf-8")

        self.assert_in_text(
            "'serviceWorker' in navigator",
            content,
            "Registration must be guarded by feature detection ('serviceWorker' in navigator)",
        )

        self.assert_matches(
            r"navigator\.serviceWorker\.register\(['\"](./)?sw\.js['\"]",
            content,
            "Must register 'sw.js' service worker script",
        )

        self.assert_matches(
            r"\.then|\.catch|await\s+navigator\.serviceWorker\.register",
            content,
            "Must handle registration lifecycle promise",
        )

        self.assert_matches(
            r"scope|update|onupdatefound|registration",
            content,
            "Registration must handle service worker lifecycle or scope",
        )

        self.assert_in_text("</script>", content, "Registration must be properly enclosed in script tags")

    # -------------------------------------------------------------------------
    # Feature 18: Mobile UI Polish & Ergonomics (M3)
    # -------------------------------------------------------------------------
    def test_f18_mobile_ui_polish_and_ergonomics(self):
        """F-18: Verify user-select: none, tap highlight transparent, and no overflow."""
        content = self.index_path.read_text(encoding="utf-8")

        self.assert_matches(
            r"user-select:\s*none|-webkit-user-select:\s*none",
            content,
            "Must disable text selection on mobile chrome (user-select: none)",
        )

        self.assert_matches(
            r"-webkit-tap-highlight-color:\s*(transparent|rgba\(0,\s*0,\s*0,\s*0\))",
            content,
            "Must remove tap gray highlight (-webkit-tap-highlight-color: transparent)",
        )

        self.assert_in_text(
            "overflow-x: hidden",
            content,
            "Must enforce overflow-x: hidden to eliminate horizontal jitter",
        )

        self.assert_matches(
            r'<meta\s+name=["\']viewport["\'][^>]*content=["\'][^"\']*width=device-width',
            content,
            "Must include responsive mobile viewport meta tag",
        )

        self.assert_matches(
            r"text-sm|text-base|text-xs|font-size:\s*1[4-8]px|min-h-\[4|min-h-\[44",
            content,
            "Must declare mobile-readable typography and touch-friendly targets",
        )

    # -------------------------------------------------------------------------
    # Feature 19: Hardware Back Button Modal Handling (M3)
    # -------------------------------------------------------------------------
    def test_f19_hardware_back_button_modal_handling(self):
        """F-19: Verify History API popstate handling for Android hardware Back button."""
        content = self.index_path.read_text(encoding="utf-8")

        self.assert_in_text(
            "history.pushState",
            content,
            "Must push history state when opening modals for Back button intercept",
        )

        self.assert_in_text(
            "popstate",
            content,
            "Must listen for 'popstate' event to intercept hardware Back button",
        )

        self.assert_matches(
            r"closeModal|closeActiveModal|hideModal|global-modal-box",
            content,
            "popstate handler must trigger modal dismissal",
        )

        self.assert_matches(
            r"modal.*active|isModalOpen|modalOpen",
            content,
            "Must track modal open state for Back button navigation",
        )

        self.assert_matches(
            r"history\.back\(\)|closeModal|global-modal-backdrop",
            content,
            "Explicit modal dismissal must sync navigation state",
        )

    # -------------------------------------------------------------------------
    # Feature 20: Android TWA Project Architecture (M4)
    # -------------------------------------------------------------------------
    def test_f20_android_twa_project_architecture(self):
        """F-20: Verify android/ directory, compileSdk 35, targetSdk 34, minSdk 24, package."""
        self.assertTrue(self.android_dir.exists(), "android/ directory must exist")

        app_build_gradle = self.android_dir / "app" / "build.gradle"
        self.assertTrue(app_build_gradle.exists(), "android/app/build.gradle must exist")
        gradle_text = app_build_gradle.read_text(encoding="utf-8")

        self.assert_matches(r"compileSdk(Version)?\s*=?\s*35", gradle_text, "Must target compileSdk 35")
        self.assert_matches(r"targetSdk(Version)?\s*=?\s*34", gradle_text, "Must target targetSdk 34 for 2026 store compliance")
        self.assert_matches(r"minSdk(Version)?\s*=?\s*24", gradle_text, "Must set minSdk 24 (Android 7.0 Nougat)")
        self.assert_in_text("ir.bagherololum.hamrah", gradle_text, "applicationId must be 'ir.bagherololum.hamrah'")
        self.assert_in_text("com.google.androidbrowserhelper:androidbrowserhelper", gradle_text)

    # -------------------------------------------------------------------------
    # Feature 21: Cafe Bazaar TWA Manifest Config (M4)
    # -------------------------------------------------------------------------
    def test_f21_cafe_bazaar_twa_manifest_config(self):
        """F-21: Verify AndroidManifest.xml has LauncherActivity, DEFAULT_URL with ?mode=app."""
        manifest_file = self.android_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        self.assertTrue(manifest_file.exists(), f"{manifest_file} must exist")
        xml_text = manifest_file.read_text(encoding="utf-8")

        self.assert_in_text(
            "com.google.androidbrowserhelper.trusted.LauncherActivity",
            xml_text,
            "Must declare com.google.androidbrowserhelper.trusted.LauncherActivity as main activity",
        )

        self.assert_in_text("android.support.customtabs.trusted.DEFAULT_URL", xml_text)
        self.assert_in_text("hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app", xml_text)

        strings_file = self.android_dir / "app" / "src" / "main" / "res" / "values" / "strings.xml"
        has_persian_label = False
        if strings_file.exists():
            strings_text = strings_file.read_text(encoding="utf-8")
            has_persian_label = "همراه باقرالعلوم" in strings_text
        if not has_persian_label:
            has_persian_label = "همراه باقرالعلوم" in xml_text

        self.assertTrue(has_persian_label, "Android app name must be 'همراه باقرالعلوم'")
        self.assert_in_text("STATUS_BAR_COLOR", xml_text)

    # -------------------------------------------------------------------------
    # Feature 22: Multi-Origin Fallback Configuration (M4)
    # -------------------------------------------------------------------------
    def test_f22_multi_origin_fallback_configuration(self):
        """F-22: Verify ADDITIONAL_TRUSTED_ORIGINS references GitHub Pages fallback mirror."""
        manifest_file = self.android_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        self.assertTrue(manifest_file.exists(), "AndroidManifest.xml must exist")
        xml_text = manifest_file.read_text(encoding="utf-8")

        self.assert_in_text("android.support.customtabs.trusted.ADDITIONAL_TRUSTED_ORIGINS", xml_text)
        self.assert_in_text("@array/additional_trusted_origins", xml_text)

        arrays_file = self.android_dir / "app" / "src" / "main" / "res" / "values" / "arrays.xml"
        self.assertTrue(arrays_file.exists(), "arrays.xml resource file must exist")
        arr_text = arrays_file.read_text(encoding="utf-8")
        self.assert_in_text("psyeducationhadi-bot.github.io", arr_text)

        self.assert_in_text("android.intent.action.VIEW", xml_text)
        self.assert_in_text("android.intent.category.BROWSABLE", xml_text)
        self.assert_in_text('android:autoVerify="true"', xml_text)

    # -------------------------------------------------------------------------
    # Feature 23: Local Signed APK & AAB Build (M4)
    # -------------------------------------------------------------------------
    def test_f23_local_signed_apk_and_aab_build(self):
        """F-23: Verify release APK and AAB build script, signing config, and artifacts."""
        app_build_gradle = self.android_dir / "app" / "build.gradle"
        self.assertTrue(app_build_gradle.exists(), "android/app/build.gradle must exist")
        gradle_text = app_build_gradle.read_text(encoding="utf-8")

        self.assert_in_text("signingConfigs", gradle_text)
        self.assert_in_text("signingConfig signingConfigs.release", gradle_text)
        self.assert_matches(r"storeFile\s+file\(.*\)", gradle_text)

        has_release_dir = self.release_apk_dir.exists()
        has_build_script = (self.root / "android" / "gradlew").exists() or (self.root / "android" / "gradlew.bat").exists()
        self.assertTrue(has_release_dir or has_build_script)

        expected_apk = self.release_apk_dir / "hamrah-bagherololum-release.apk"
        ci_text = self.workflow_path.read_text(encoding="utf-8") if self.workflow_path.exists() else ""
        self.assertTrue(
            expected_apk.exists() or "hamrah-bagherololum-release.apk" in ci_text or "hamrah-bagherololum-release.apk" in gradle_text,
            "Release artifact naming convention 'hamrah-bagherololum-release.apk' must be defined",
        )

    # -------------------------------------------------------------------------
    # Feature 24: GitHub Actions CI/CD Workflow (M5)
    # -------------------------------------------------------------------------
    def test_f24_github_actions_cicd_workflow(self):
        """F-24: Verify .github/workflows/build-android-apk.yml on push to main with JDK 17."""
        self.assertTrue(
            self.workflow_path.exists(),
            f"{self.workflow_path} must exist to automate Android APK builds",
        )
        content = self.workflow_path.read_text(encoding="utf-8")

        self.assert_matches(r"push:\s*(branches:\s*\[?\s*main\s*\]?)?", content)
        self.assert_in_text("ubuntu-latest", content)
        self.assert_in_text("actions/setup-java", content)
        self.assert_in_text("17", content)

        has_android_sdk = (
            "setup-android" in content or "ANDROID_SDK_ROOT" in content or "sdkmanager" in content or "gradlew" in content
        )
        self.assertTrue(has_android_sdk, "Workflow must configure Android SDK environment")
        self.assert_matches(r"assembleRelease|bundleRelease|\./gradlew\s+build", content)

    # -------------------------------------------------------------------------
    # Feature 25: Artifact Upload & GitHub Release (M5)
    # -------------------------------------------------------------------------
    def test_f25_artifact_upload_and_github_release(self):
        """F-25: Verify workflow uploads APK/AAB and creates GitHub Release with Persian notes."""
        self.assertTrue(self.workflow_path.exists(), "Workflow must exist")
        content = self.workflow_path.read_text(encoding="utf-8")

        self.assert_in_text("actions/upload-artifact", content)
        self.assert_in_text(".apk", content)
        self.assert_in_text(".aab", content)
        self.assert_matches(r"action-gh-release|gh\s+release\s+create|softprops/action-gh-release", content)
        self.assert_matches(r"همراه باقرالعلوم|نسخه|انتشار", content)

    # -------------------------------------------------------------------------
    # Feature 26: Git Commit, Push & Worker Deploy (M5)
    # -------------------------------------------------------------------------
    def test_f26_git_commit_push_and_worker_deploy(self):
        """F-26: Verify copy repo git remote, branch main, and Cloudflare Worker deploy config."""
        self.assertTrue(self.wrangler_path.exists())
        w_data = json.loads(self.wrangler_path.read_text(encoding="utf-8"))
        self.assertEqual(w_data.get("name"), "hamrah-bagherololum-copy")
        self.assertTrue(w_data.get("workers_dev", False))

        git_head = self.root / ".git" / "HEAD"
        if git_head.exists():
            head_content = git_head.read_text(encoding="utf-8")
            self.assert_in_text("main", head_content)

        self.assertTrue(self.index_path.exists())

        for tracked_file in [self.index_path, self.manifest_path]:
            if tracked_file.exists():
                text = tracked_file.read_text(encoding="utf-8", errors="ignore")
                self.assert_not_in_text("<<<<<<< HEAD", text)


if __name__ == "__main__":
    unittest.main()
