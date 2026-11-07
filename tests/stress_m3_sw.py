#!/usr/bin/env python3
"""Milestone 3 Service Worker, Offline Fallback, and Caching Empirical Stress Test Suite.

Adversarially challenges and empirically verifies:
1. Request Discrimination:
   - Evaluates mode === 'navigate', destination === 'document', or accept: text/html.
   - NEVER serves offline.html for failed API requests or failed static asset requests.
2. Cache Bypass Check:
   - Dynamic API requests (db.json, .json, /api/, workers.dev) and HTML navigation
     strictly use { cache: 'no-store' } to guarantee real-time CMS sync.
3. Pre-cache Completeness:
   - PRECACHE_URLS entries resolve to real files on disk with non-zero size.
   - Validates install and activate lifecycle events.
4. Offline Page Self-Containment:
   - Standalone offline.html contains ZERO external resource requests (no CDN stylesheets,
     no external scripts, no external fonts or images).
   - Validates Persian RTL layout, navy dark palette, reload button, and auto-refresh listener.
5. Headless Chrome Live DOM Rendering:
   - Validates offline.html rendering under Headless Google Chrome.
6. Adversarial Attack Surface & Failure Mode Mining:
   - Evaluates behavior of static asset requests on Cloudflare Workers origin vs GitHub Pages origin.
"""

import json
import os
import re
import struct
import subprocess
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SW_PATH = PROJECT_ROOT / "sw.js"
OFFLINE_PATH = PROJECT_ROOT / "offline.html"
INDEX_PATH = PROJECT_ROOT / "index.html"
MANIFEST_PATH = PROJECT_ROOT / "manifest.json"
ICONS_DIR = PROJECT_ROOT / "icons"
CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def run_node_harness(harness_code: str) -> dict:
    """Executes a Node.js snippet and returns the parsed JSON output."""
    full_script = f"""
    const fs = require('fs');
    const vm = require('vm');
    const path = require('path');

    try {{
        {harness_code}
    }} catch (err) {{
        console.log(JSON.stringify({{ error: err.message, stack: err.stack }}));
    }}
    """
    proc = subprocess.run(
        ["node", "-e", full_script],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node execution failed (code {proc.returncode}):\n{proc.stderr}")
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError(f"Node produced empty output. stderr: {proc.stderr}")
    try:
        return json.loads(out)
    except json.JSONDecodeError as jde:
        raise RuntimeError(f"Failed to parse Node JSON output:\n{out}\nError: {jde}")


class TestM3ServiceWorkerRequestDiscrimination(unittest.TestCase):
    """Adversarial stress-testing of SW fetch handler routing and request discrimination."""

    def setUp(self):
        self.assertTrue(SW_PATH.exists(), f"sw.js must exist at {SW_PATH}")
        self.sw_content = SW_PATH.read_text(encoding="utf-8")

    def test_static_navigation_discrimination_logic(self):
        """Verify sw.js logic explicitly checks navigate mode, document destination, or text/html."""
        has_nav_mode = bool(re.search(r"mode\s*===?\s*['\"]navigate['\"]", self.sw_content))
        has_doc_dest = bool(re.search(r"destination\s*===?\s*['\"]document['\"]", self.sw_content))
        has_accept_html = bool(re.search(r"text/html", self.sw_content))

        self.assertTrue(
            has_nav_mode or has_doc_dest or has_accept_html,
            "sw.js must evaluate request.mode === 'navigate', request.destination === 'document', or text/html accept header",
        )

    def test_request_discrimination_never_serves_offline_html_to_api_or_assets(self):
        """Verify that offline.html is NEVER served for failed API requests or failed static asset requests."""
        js_harness = f"""
        const swCode = fs.readFileSync({json.dumps(str(SW_PATH).replace('\\\\', '/'))}, 'utf8');

        const listeners = {{}};
        const mockCaches = new Map();
        const cacheStore = {{
            open: async (name) => {{
                if (!mockCaches.has(name)) mockCaches.set(name, new Map());
                const current = mockCaches.get(name);
                return {{
                    addAll: async (urls) => {{
                        for (const u of urls) current.set(u, new Response('cached:' + u, {{ status: 200 }}));
                    }},
                    match: async (req) => {{
                        const key = typeof req === 'string' ? req : req.url;
                        return current.get(key) || null;
                    }},
                    put: async (req, res) => {{
                        const key = typeof req === 'string' ? req : req.url;
                        current.set(key, res);
                    }}
                }};
            }},
            keys: async () => Array.from(mockCaches.keys()),
            delete: async (k) => mockCaches.delete(k),
            match: async (req) => {{
                const key = typeof req === 'string' ? req : req.url;
                for (const [, cache] of mockCaches) {{
                    if (cache.has(key)) return cache.get(key);
                }}
                return null;
            }}
        }};

        // Simulate complete network blackout
        const mockFetch = async () => {{
            throw new Error('Network offline failure simulation');
        }};

        const sandbox = {{
            self: {{
                addEventListener: (type, fn) => {{
                    listeners[type] = listeners[type] || [];
                    listeners[type].push(fn);
                }},
                skipWaiting: async () => {{}},
                clients: {{ claim: async () => {{}} }}
            }},
            caches: cacheStore,
            fetch: mockFetch,
            Response: globalThis.Response,
            URL: globalThis.URL,
            console: {{ log: () => {{}}, warn: () => {{}}, error: () => {{}} }}
        }};

        vm.runInNewContext(swCode, sandbox);

        async function simulateFetch(reqData) {{
            const fetchListeners = listeners['fetch'] || [];
            let responsePromise = null;
            const event = {{
                request: {{
                    method: reqData.method || 'GET',
                    url: reqData.url,
                    mode: reqData.mode || 'cors',
                    destination: reqData.destination || '',
                    headers: {{
                        get: (k) => (reqData.headers || {{}})[k.toLowerCase()] || null
                    }}
                }},
                respondWith: (promise) => {{ responsePromise = promise; }}
            }};

            for (const fn of fetchListeners) fn(event);

            if (!responsePromise) return {{ intercepted: false }};

            const res = await responsePromise;
            const body = await res.text();
            return {{
                intercepted: true,
                status: res.status,
                contentType: res.headers ? res.headers.get('content-type') : null,
                body: body
            }};
        }}

        (async () => {{
            // Pre-seed offline.html in cache
            const cache = await cacheStore.open('hamrah-bagherololum-v1');
            await cache.put('./offline.html', new Response('<!DOCTYPE html><html>OFFLINE_HTML_DOC</html>', {{
                status: 200,
                headers: {{ 'Content-Type': 'text/html; charset=utf-8' }}
            }}));

            // 1. Navigation offline -> SHOULD serve offline.html
            const nav = await simulateFetch({{
                url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/',
                mode: 'navigate',
                destination: 'document',
                headers: {{ 'accept': 'text/html' }}
            }});

            // 2. Failed API db.json -> MUST NOT serve offline.html
            const apiDb = await simulateFetch({{
                url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/db.json',
                mode: 'cors',
                headers: {{ 'accept': 'application/json' }}
            }});

            // 3. Failed API /api/data -> MUST NOT serve offline.html
            const apiEndpoint = await simulateFetch({{
                url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/api/data',
                mode: 'cors',
                headers: {{ 'accept': 'application/json' }}
            }});

            // 4. Failed static asset on GitHub Pages mirror -> MUST NOT serve offline.html
            const staticAssetPages = await simulateFetch({{
                url: 'https://psyeducationhadi-bot.github.io/hamrah-bagherololum-copy/missing-theme.css',
                mode: 'no-cors',
                destination: 'style',
                headers: {{ 'accept': 'text/css' }}
            }});

            // 5. Failed static image asset on Workers origin -> MUST NOT serve offline.html
            const staticImgWorkers = await simulateFetch({{
                url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/icons/missing.png',
                mode: 'no-cors',
                destination: 'image',
                headers: {{ 'accept': 'image/png' }}
            }});

            console.log(JSON.stringify({{
                nav,
                apiDb,
                apiEndpoint,
                staticAssetPages,
                staticImgWorkers
            }}));
        }})();
        """
        res = run_node_harness(js_harness)

        # 1. Navigation receives offline.html
        self.assertTrue(res["nav"]["intercepted"])
        self.assertIn("OFFLINE_HTML_DOC", res["nav"]["body"])

        # 2. API db.json NEVER receives offline.html
        api_db = res["apiDb"]
        self.assertTrue(api_db["intercepted"])
        self.assertEqual(api_db["status"], 503)
        self.assertNotIn("OFFLINE_HTML_DOC", api_db["body"])
        self.assertNotIn("<html", api_db["body"].lower())
        self.assertIn("application/json", api_db.get("contentType", ""))

        # 3. API /api/data NEVER receives offline.html
        api_ep = res["apiEndpoint"]
        self.assertTrue(api_ep["intercepted"])
        self.assertEqual(api_ep["status"], 503)
        self.assertNotIn("OFFLINE_HTML_DOC", api_ep["body"])
        self.assertNotIn("<html", api_ep["body"].lower())
        self.assertIn("application/json", api_ep.get("contentType", ""))

        # 4. Static asset on GitHub Pages NEVER receives offline.html (returns 408)
        st_pages = res["staticAssetPages"]
        self.assertTrue(st_pages["intercepted"])
        self.assertEqual(st_pages["status"], 408)
        self.assertNotIn("OFFLINE_HTML_DOC", st_pages["body"])
        self.assertNotIn("<html", st_pages["body"].lower())

        # 5. Static asset on Workers origin NEVER receives offline.html
        st_workers = res["staticImgWorkers"]
        self.assertTrue(st_workers["intercepted"])
        self.assertNotIn("OFFLINE_HTML_DOC", st_workers["body"])
        self.assertNotIn("<html", st_workers["body"].lower())


class TestM3ServiceWorkerCacheBypass(unittest.TestCase):
    """Adversarial stress-testing of { cache: 'no-store' } cache bypass."""

    def setUp(self):
        self.sw_content = SW_PATH.read_text(encoding="utf-8")

    def test_static_cache_bypass_syntax(self):
        """Verify sw.js explicitly passes { cache: 'no-store' } to fetch calls for dynamic & nav requests."""
        matches = re.findall(r"fetch\s*\([^,)]+,\s*\{\s*cache:\s*['\"]no-store['\"]\s*\}\)", self.sw_content)
        self.assertGreaterEqual(
            len(matches),
            2,
            "sw.js must contain at least two fetch calls configured with { cache: 'no-store' } (navigation & dynamic data)",
        )

    def test_empirical_cache_bypass_for_dynamic_and_navigation(self):
        """Verify all dynamic API requests (db.json, .json, /api/, workers.dev) and HTML navigation use { cache: 'no-store' }."""
        js_harness = f"""
        const swCode = fs.readFileSync({json.dumps(str(SW_PATH).replace('\\\\', '/'))}, 'utf8');

        const listeners = {{}};
        const fetchCalls = [];

        const mockFetch = async (req, opts = {{}}) => {{
            const urlStr = typeof req === 'string' ? req : req.url;
            fetchCalls.push({{ url: urlStr, opts }});
            return new Response('OK', {{ status: 200 }});
        }};

        const sandbox = {{
            self: {{
                addEventListener: (type, fn) => {{
                    listeners[type] = listeners[type] || [];
                    listeners[type].push(fn);
                }},
                skipWaiting: async () => {{}},
                clients: {{ claim: async () => {{}} }}
            }},
            caches: {{
                open: async () => ({{
                    addAll: async () => {{}},
                    match: async () => null,
                    put: async () => {{}}
                }}),
                match: async () => null
            }},
            fetch: mockFetch,
            Response: globalThis.Response,
            URL: globalThis.URL,
            console: {{ log: () => {{}}, warn: () => {{}}, error: () => {{}} }}
        }};

        vm.runInNewContext(swCode, sandbox);

        async function triggerFetch(url, mode, dest, headers = {{}}) {{
            const event = {{
                request: {{
                    method: 'GET',
                    url: url,
                    mode: mode,
                    destination: dest,
                    headers: {{ get: (k) => headers[k.toLowerCase()] || null }}
                }},
                respondWith: (p) => p
            }};
            const fn = listeners['fetch'][0];
            await fn(event);
        }}

        (async () => {{
            // 1. Navigation HTML
            await triggerFetch('https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app', 'navigate', 'document', {{ accept: 'text/html' }});
            // 2. Dynamic db.json
            await triggerFetch('https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/db.json', 'cors', '');
            // 3. Dynamic /api/ endpoint
            await triggerFetch('https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/api/scores', 'cors', '');
            // 4. Dynamic workers.dev API endpoint
            await triggerFetch('https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/data.json', 'cors', '');
            // 5. Static asset on GitHub Pages mirror (should NOT force no-store)
            await triggerFetch('https://psyeducationhadi-bot.github.io/hamrah-bagherololum-copy/icons/icon-192.png', 'no-cors', 'image');

            console.log(JSON.stringify({{ fetchCalls }}));
        }})();
        """
        res = run_node_harness(js_harness)
        calls = res["fetchCalls"]
        self.assertEqual(len(calls), 5, f"Expected 5 fetch calls, got {len(calls)}")

        # Call 1: Navigation -> MUST have cache: 'no-store'
        self.assertEqual(calls[0]["opts"].get("cache"), "no-store", "HTML navigation fetch must use { cache: 'no-store' }")

        # Call 2: db.json -> MUST have cache: 'no-store'
        self.assertEqual(calls[1]["opts"].get("cache"), "no-store", "db.json dynamic fetch must use { cache: 'no-store' }")

        # Call 3: /api/ -> MUST have cache: 'no-store'
        self.assertEqual(calls[2]["opts"].get("cache"), "no-store", "/api/ dynamic fetch must use { cache: 'no-store' }")

        # Call 4: .json / workers.dev -> MUST have cache: 'no-store'
        self.assertEqual(calls[3]["opts"].get("cache"), "no-store", "workers.dev dynamic API fetch must use { cache: 'no-store' }")

        # Call 5: Static image on GitHub Pages -> does NOT force no-store
        self.assertNotEqual(calls[4]["opts"].get("cache"), "no-store", "Static asset fetch should allow browser/sw caching")


class TestM3PrecacheCompleteness(unittest.TestCase):
    """Adversarial stress-testing of PRECACHE_URLS and filesystem integrity."""

    def setUp(self):
        self.sw_content = SW_PATH.read_text(encoding="utf-8")

    def test_precache_urls_array_exists_and_non_empty(self):
        """Extract PRECACHE_URLS from sw.js and verify entries."""
        match = re.search(r"PRECACHE_URLS\s*=\s*\[(.*?)\]", self.sw_content, re.DOTALL)
        self.assertIsNotNone(match, "PRECACHE_URLS array must be defined in sw.js")
        entries = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
        self.assertGreaterEqual(len(entries), 3, "PRECACHE_URLS must contain at least 3 essential assets")

        # Check offline.html is present
        self.assertTrue(any("offline.html" in e for e in entries), "offline.html must be in PRECACHE_URLS")

        # Check 192 and 512 icons are present
        self.assertTrue(any("192" in e for e in entries), "192px icon must be in PRECACHE_URLS")
        self.assertTrue(any("512" in e for e in entries), "512px icon must be in PRECACHE_URLS")

    def test_every_precache_url_exists_on_disk_and_nonzero_size(self):
        """Every single file in PRECACHE_URLS must physically exist on disk with > 0 bytes."""
        match = re.search(r"PRECACHE_URLS\s*=\s*\[(.*?)\]", self.sw_content, re.DOTALL)
        entries = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))

        for entry in entries:
            clean = entry.lstrip("./").lstrip("/")
            file_path = PROJECT_ROOT / clean
            self.assertTrue(
                file_path.exists(),
                f"Pre-cached asset '{entry}' resolved to '{file_path}' which DOES NOT exist on disk!",
            )
            file_size = file_path.stat().st_size
            self.assertGreater(
                file_size,
                0,
                f"Pre-cached asset '{entry}' at '{file_path}' is an empty file (0 bytes)!",
            )

            # If it's a PNG icon, check magic bytes and dimensions
            if file_path.suffix.lower() == ".png":
                with open(file_path, "rb") as pf:
                    hdr = pf.read(24)
                self.assertTrue(hdr.startswith(b"\x89PNG\r\n\x1a\n"), f"{entry} lacks PNG magic bytes")
                w, h = struct.unpack(">II", hdr[16:24])
                self.assertIn(w, [192, 512], f"Icon {entry} width unexpected: {w}")
                self.assertEqual(w, h, f"Icon {entry} must be square")

    def test_activate_event_purges_stale_caches(self):
        """Simulate activate event in Node.js and verify older cache generations are deleted."""
        js_harness = f"""
        const swCode = fs.readFileSync({json.dumps(str(SW_PATH).replace('\\\\', '/'))}, 'utf8');

        const listeners = {{}};
        const activeCaches = new Set(['hamrah-bagherololum-v0', 'hamrah-bagherololum-v1', 'obsolete-cache-123']);
        let clientsClaimCalled = false;

        const sandbox = {{
            self: {{
                addEventListener: (type, fn) => {{
                    listeners[type] = listeners[type] || [];
                    listeners[type].push(fn);
                }},
                skipWaiting: async () => {{}},
                clients: {{
                    claim: async () => {{ clientsClaimCalled = true; }}
                }}
            }},
            caches: {{
                open: async () => ({{ addAll: async () => {{}} }}),
                keys: async () => Array.from(activeCaches),
                delete: async (k) => {{
                    activeCaches.delete(k);
                    return true;
                }}
            }},
            fetch: async () => {{}},
            Response: globalThis.Response,
            URL: globalThis.URL,
            console: {{ log: () => {{}}, warn: () => {{}}, error: () => {{}} }}
        }};

        vm.runInNewContext(swCode, sandbox);

        (async () => {{
            const activateFns = listeners['activate'] || [];
            for (const fn of activateFns) {{
                let waitPromise;
                fn({{ waitUntil: (p) => {{ waitPromise = p; }} }});
                if (waitPromise) await waitPromise;
            }}

            console.log(JSON.stringify({{
                clientsClaimCalled,
                remainingCaches: Array.from(activeCaches)
            }}));
        }})();
        """
        res = run_node_harness(js_harness)
        self.assertTrue(res.get("clientsClaimCalled"), "clients.claim() must be called on SW activate")
        remaining = res.get("remainingCaches", [])
        self.assertEqual(
            remaining,
            ["hamrah-bagherololum-v1"],
            f"Activate must delete obsolete caches, remaining were: {remaining}",
        )


class TestM3OfflinePageSelfContainment(unittest.TestCase):
    """Adversarial stress-testing of offline.html self-containment and Persian RTL layout."""

    def setUp(self):
        self.assertTrue(OFFLINE_PATH.exists(), f"offline.html must exist at {OFFLINE_PATH}")
        self.html_text = OFFLINE_PATH.read_text(encoding="utf-8")
        self.soup = BeautifulSoup(self.html_text, "html.parser")

    def test_zero_external_stylesheets(self):
        """offline.html must contain ZERO external stylesheet links."""
        link_tags = self.soup.find_all("link")
        for link in link_tags:
            rel = [r.lower() for r in link.get("rel", [])] if isinstance(link.get("rel"), list) else [str(link.get("rel", "")).lower()]
            if "stylesheet" in rel:
                href = link.get("href", "")
                self.fail(f"offline.html must not load external stylesheets! Found: <link rel='stylesheet' href='{href}'>")

    def test_zero_external_scripts(self):
        """offline.html must contain ZERO external script references."""
        script_tags = self.soup.find_all("script")
        for script in script_tags:
            src = script.get("src")
            if src:
                self.fail(f"offline.html must not load external scripts! Found: <script src='{src}'>")

    def test_zero_external_images_or_multimedia(self):
        """offline.html must contain ZERO external images, media, or iframes."""
        for tag_name in ["img", "iframe", "video", "audio", "source", "embed", "object"]:
            for el in self.soup.find_all(tag_name):
                src = el.get("src") or el.get("data")
                if src and (src.startswith("http://") or src.startswith("https://") or src.startswith("//")):
                    self.fail(f"offline.html must not load external {tag_name}! Found src: {src}")

    def test_zero_remote_css_imports_or_remote_fonts(self):
        """Inline styles in offline.html must NOT reference remote @import or remote url()."""
        style_tags = self.soup.find_all("style")
        self.assertGreater(len(style_tags), 0, "offline.html must contain inline <style> block")

        for style in style_tags:
            text = style.get_text()
            remote_imports = re.findall(r"@import\s+(?:url\(['\"]?|['\"])(https?://|//)[^'\")]+", text, re.I)
            self.assertEqual(len(remote_imports), 0, f"Found remote @import in offline.html style: {remote_imports}")

            remote_urls = re.findall(r"url\(['\"]?(https?://|//)[^'\")]+", text, re.I)
            self.assertEqual(len(remote_urls), 0, f"Found remote url() in offline.html style: {remote_urls}")

    def test_persian_rtl_and_brand_adherence(self):
        """offline.html must be configured with fa-IR, rtl, dark navy palette, and Persian text."""
        html_tag = self.soup.find("html")
        self.assertIsNotNone(html_tag)
        lang = html_tag.get("lang", "")
        dir_attr = html_tag.get("dir", "")
        self.assertIn("fa", lang.lower(), "html lang must be Persian (fa or fa-IR)")
        self.assertEqual(dir_attr.lower(), "rtl", "html dir must be rtl")

        # Color palette: #0f172a, #0f2442, or navy
        self.assertTrue(
            bool(re.search(r"#0f172a|#0f2442|#1e3a5f|navy", self.html_text, re.I)),
            "offline.html must adhere to dark navy palette (#0f172a, #0f2442, #1e3a5f)",
        )

        # Persian explanation keywords
        self.assertTrue(
            bool(re.search(r"اتصال|اینترنت|آفلاین", self.html_text)),
            "offline.html must provide Persian explanation of connectivity failure",
        )

        # Retry button
        retry_btn = self.soup.find(lambda el: el.name in ["button", "a"] and "تلاش مجدد" in el.get_text())
        self.assertIsNotNone(retry_btn, "offline.html must have a prominent 'تلاش مجدد' (Retry) button")

        # Reload invocation
        self.assertTrue(
            bool(re.search(r"location\.reload\(\)|window\.location\.reload\(\)", self.html_text)),
            "offline.html retry button must trigger window.location.reload()",
        )

        # Auto-refresh on 'online' event
        self.assertTrue(
            bool(re.search(r"addEventListener\(['\"]online['\"]", self.html_text)),
            "offline.html must listen for 'online' event to auto-refresh",
        )

    def test_live_chrome_renders_offline_fallback(self):
        """Headless Chrome: render offline.html and verify DOM contains retry button and Persian text."""
        if not CHROME_PATH.exists():
            self.skipTest("Google Chrome not available on this system")

        url = f"file:///{OFFLINE_PATH.as_posix()}"
        proc = subprocess.run(
            [str(CHROME_PATH), "--headless=new", "--disable-gpu", "--dump-dom", url],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(proc.returncode, 0, f"Chrome failed: {proc.stderr}")
        dom = proc.stdout
        self.assertIn("ارتباط با اینترنت برقرار نیست", dom)
        self.assertIn("تلاش مجدد", dom)
        self.assertIn("dir=\"rtl\"", dom)


class TestM3MobileUIPolishAndErgonomics(unittest.TestCase):
    """Adversarial stress-testing of mobile touch ergonomic requirements in index.html."""

    def setUp(self):
        self.html_text = INDEX_PATH.read_text(encoding="utf-8")

    def test_viewport_meta_tag(self):
        """Viewport meta must specify width=device-width."""
        match = re.search(r'<meta\s+name=["\']viewport["\'][^>]*content=["\']([^"\']+)["\']', self.html_text, re.I)
        self.assertIsNotNone(match, "Viewport meta tag must be present")
        content = match.group(1)
        self.assertIn("width=device-width", content)
        self.assertIn("initial-scale=1.0", content)

    def test_mobile_touch_css_polish(self):
        """Verify -webkit-tap-highlight-color: transparent and user-select: none."""
        self.assertTrue(
            bool(re.search(r"-webkit-tap-highlight-color:\s*transparent", self.html_text)),
            "Interactive chrome must suppress tap gray highlight with -webkit-tap-highlight-color: transparent",
        )
        self.assertTrue(
            bool(re.search(r"user-select:\s*none|-webkit-user-select:\s*none", self.html_text)),
            "Chrome UI must prevent unwanted text selection with user-select: none",
        )
        self.assertIn(
            "overflow-x: hidden",
            self.html_text,
            "html/body must enforce overflow-x: hidden to prevent horizontal page jitter",
        )

    def test_hardware_back_button_modal_handling(self):
        """Verify History API pushState/popstate intercepts hardware Back button to dismiss open modals."""
        self.assertIn("popstate", self.html_text, "index.html must register popstate event listener")
        self.assertIn("pushState", self.html_text, "openModal must invoke history.pushState")
        self.assertTrue(
            bool(re.search(r"closeModal|hideModal", self.html_text)),
            "popstate handler must invoke modal closing routine",
        )


class TestM3AdversarialVulnerabilityAnalysis(unittest.TestCase):
    """Deep adversarial white-box vulnerability mining on Service Worker cache interaction."""

    def setUp(self):
        self.sw_content = SW_PATH.read_text(encoding="utf-8")

    def test_vulnerability_workers_dev_wildcard_intercepts_static_assets(self):
        """EMPIRICAL CHALLENGE: Verify whether static assets on workers.dev origin are hijacked by dynamic API handler.

        When sw.js line 102 checks url.hostname.includes('workers.dev'), it does not exclude static assets
        (e.g., .png, .css, .woff2) or check destination !== 'image'.
        As a result, on the primary production origin (hamrah-bagherololum-copy.psyeducation-hadi.workers.dev),
        static assets bypass Cache-First logic and return 503 JSON when offline instead of the pre-cached file.
        """
        js_harness = f"""
        const swCode = fs.readFileSync({json.dumps(str(SW_PATH).replace('\\\\', '/'))}, 'utf8');

        const listeners = {{}};
        const cacheStore = new Map();

        const sandbox = {{
            self: {{
                addEventListener: (type, fn) => {{
                    listeners[type] = listeners[type] || [];
                    listeners[type].push(fn);
                }},
                skipWaiting: async () => {{}},
                clients: {{ claim: async () => {{}} }}
            }},
            caches: {{
                open: async (name) => ({{
                    addAll: async (urls) => {{
                        for (const u of urls) cacheStore.set(u, new Response('PRECACHED_PNG', {{ status: 200 }}));
                    }},
                    match: async (url) => cacheStore.get(url) || null
                }}),
                match: async (req) => cacheStore.get(typeof req === 'string' ? req : req.url) || null
            }},
            fetch: async () => {{ throw new Error('Offline (no network connection)'); }},
            Response: globalThis.Response,
            URL: globalThis.URL,
            console: {{ log: () => {{}}, warn: () => {{}}, error: () => {{}} }}
        }};

        vm.runInNewContext(swCode, sandbox);

        (async () => {{
            // Install sw.js to populate cache with PRECACHE_URLS
            await listeners['install'][0]({{ waitUntil: async (p) => await p }});

            // Simulate requesting pre-cached icon on Cloudflare Workers origin while offline
            let responsePromise;
            listeners['fetch'][0]({{
                request: {{
                    method: 'GET',
                    url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/icons/icon-192.png',
                    mode: 'no-cors',
                    destination: 'image',
                    headers: {{ get: () => 'image/png' }}
                }},
                respondWith: (p) => {{ responsePromise = p; }}
            }});

            const res = await responsePromise;
            const body = await res.text();
            console.log(JSON.stringify({{
                status: res.status,
                contentType: res.headers.get('content-type'),
                body: body,
                isPrecachedServed: body.includes('PRECACHED_PNG'),
                isDynamicJsonReturned: body.includes('Network unavailable')
            }}));
        }})();
        """
        res = run_node_harness(js_harness)
        # Verify that remediation successfully prevents static asset hijacking:
        self.assertEqual(res.get("status"), 200, "Remediation verified: status must be 200 for pre-cached asset")
        self.assertTrue(
            res.get("isPrecachedServed"),
            "Remediation verified: pre-cached asset must be served from Cache Storage"
        )
        self.assertFalse(
            res.get("isDynamicJsonReturned"),
            "Remediation verified: dynamic JSON 503 must not be returned for static assets"
        )


if __name__ == "__main__":
    unittest.main()
