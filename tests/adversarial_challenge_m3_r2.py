#!/usr/bin/env python3
"""Adversarial Challenge & Stress Verification Suite - Milestone 3 Round 2.

Author: m3_challenger_1_r2 (Role: critic, specialist)
Objective: Empirically stress-test sw.js Service Worker implementation:
1. Static vs Dynamic request discrimination across workers.dev and custom origins.
2. Offline behavior for pre-cached assets (HTTP 200 from cache, no 503 JSON).
3. Query parameters on pre-cached and dynamic assets (?v=1, ?ts=..., cache-busting).
4. Case-sensitivity & uppercase file extensions (.PNG, .CSS, .JS, .WOFF2, etc.).
5. Cross-origin static assets (fonts.gstatic.com, cdnjs.cloudflare.com).
6. Non-HTTP protocols (data:, chrome-extension:), non-GET methods (POST, PUT).
7. Navigation requests (offline.html fallback, no JSON fallback).
8. Dynamic API requests (db.json, /api/, workers.dev paths) retain strict Network-First.
"""

import json
import os
import re
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SW_PATH = PROJECT_ROOT / "sw.js"


def execute_sw_node_harness(test_scenario_js: str) -> dict:
    """Executes a Node.js harness providing the ServiceWorker Global Scope."""
    full_code = f"""
    const fs = require('fs');
    const vm = require('vm');

    try {{
        const swContent = fs.readFileSync({json.dumps(str(SW_PATH).replace('\\\\', '/'))}, 'utf8');

        const listeners = {{}};
        const cacheStore = new Map();

        // Realistic Cache Mock
        const mockCache = {{
            addAll: async (urls) => {{
                for (const u of urls) {{
                    cacheStore.set(u, new Response('PRECACHED_CONTENT_FOR:' + u, {{
                        status: 200,
                        headers: {{ 'Content-Type': u.endsWith('.png') ? 'image/png' : 'text/html' }}
                    }}));
                }}
            }},
            match: async (req, opts = {{}}) => {{
                const key = typeof req === 'string' ? req : req.url;
                if (cacheStore.has(key)) return cacheStore.get(key).clone();
                // Also check without query string if not found
                if (opts.ignoreSearch) {{
                    const urlWithoutSearch = key.split('?')[0];
                    if (cacheStore.has(urlWithoutSearch)) return cacheStore.get(urlWithoutSearch).clone();
                }}
                return null;
            }},
            put: async (req, res) => {{
                const key = typeof req === 'string' ? req : req.url;
                cacheStore.set(key, res);
            }}
        }};

        const cacheManager = {{
            open: async (name) => mockCache,
            keys: async () => ['hamrah-bagherololum-v1'],
            delete: async (name) => true,
            match: async (req, opts) => mockCache.match(req, opts)
        }};

        let networkOnline = false;
        let lastFetchCall = null;
        const fetchHistory = [];

        const mockFetch = async (req, opts = {{}}) => {{
            const urlStr = typeof req === 'string' ? req : req.url;
            lastFetchCall = {{ url: urlStr, opts }};
            fetchHistory.push({{ url: urlStr, opts }});
            if (!networkOnline) {{
                throw new Error('TypeError: Failed to fetch (Offline)');
            }}
            const netRes = new Response('NETWORK_OK:' + urlStr, {{
                status: 200,
                headers: {{ 'Content-Type': 'text/plain' }}
            }});
            Object.defineProperty(netRes, 'type', {{ value: 'basic' }});
            return netRes;
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
            caches: cacheManager,
            fetch: mockFetch,
            Response: globalThis.Response,
            URL: globalThis.URL,
            console: {{ log: () => {{}}, warn: () => {{}}, error: () => {{}} }}
        }};

        vm.runInNewContext(swContent, sandbox);

        // Pre-run install event to prime cache
        async function initSW() {{
            const installFns = listeners['install'] || [];
            for (const fn of installFns) {{
                let p;
                fn({{ waitUntil: (prom) => {{ p = prom; }} }});
                if (p) await p;
            }}
        }}

        async function dispatchFetch(reqOptions) {{
            let respondWithPromise = null;
            const event = {{
                request: {{
                    method: reqOptions.method || 'GET',
                    url: reqOptions.url,
                    mode: reqOptions.mode || 'cors',
                    destination: reqOptions.destination || '',
                    headers: {{
                        get: (k) => {{
                            const h = reqOptions.headers || {{}};
                            for (const [key, val] of Object.entries(h)) {{
                                if (key.toLowerCase() === k.toLowerCase()) return val;
                            }}
                            return null;
                        }}
                    }}
                }},
                respondWith: (p) => {{ respondWithPromise = p; }}
            }};

            const fetchFns = listeners['fetch'] || [];
            for (const fn of fetchFns) fn(event);

            if (!respondWithPromise) {{
                return {{ intercepted: false }};
            }}

            const response = await respondWithPromise;
            const body = await response.text();
            const ct = response.headers ? response.headers.get('content-type') : null;
            return {{
                intercepted: true,
                status: response.status,
                contentType: ct,
                body: body
            }};
        }}

        (async () => {{
            await initSW();
            {test_scenario_js}
        }})();

    }} catch (e) {{
        console.log(JSON.stringify({{ error: e.message, stack: e.stack }}));
    }}
    """;

    proc = subprocess.run(
        ["node", "-e", full_code],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node execution error ({proc.returncode}):\n{proc.stderr}")
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError(f"Node returned empty stdout. stderr: {proc.stderr}")
    return json.loads(out)


class TestM3AdversarialChallengeR2(unittest.TestCase):
    """Empirical adversarial challenge suite for Milestone 3 Service Worker."""

    def test_challenge_precached_assets_offline_on_workers_origin(self):
        """CHALLENGE 1: Pre-cached icons on hamrah-bagherololum-copy.psyeducation-hadi.workers.dev
        must return HTTP 200 from cache when offline, NOT 503 JSON.
        """
        js = """
        networkOnline = false;
        const icon192 = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/icons/icon-192.png',
            destination: 'image',
            headers: { 'accept': 'image/png' }
        });
        const icon512 = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/icons/icon-512.png',
            destination: 'image',
            headers: { 'accept': 'image/png' }
        });
        console.log(JSON.stringify({ icon192, icon512 }));
        """
        res = execute_sw_node_harness(js)
        for key in ["icon192", "icon512"]:
            item = res[key]
            self.assertTrue(item["intercepted"], f"{key} should be intercepted")
            self.assertEqual(item["status"], 200, f"{key} status must be 200 OK")
            self.assertIn("PRECACHED_CONTENT_FOR:", item["body"])
            self.assertNotIn("Network unavailable", item["body"])
            self.assertNotIn('"offline":true', item["body"])

    def test_challenge_query_string_on_static_assets(self):
        """CHALLENGE 2: Query parameters on static assets (e.g. icon-192.png?v=2026.1).
        Pathname regex must ignore query strings and routing must fall back to pre-cached asset.
        """
        js = """
        networkOnline = false;
        const queriedIcon = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/icons/icon-192.png?v=2026.1&cache_bust=xyz',
            destination: 'image',
            headers: { 'accept': 'image/png' }
        });
        console.log(JSON.stringify({ queriedIcon }));
        """
        res = execute_sw_node_harness(js)
        item = res["queriedIcon"]
        self.assertTrue(item["intercepted"])
        self.assertEqual(item["status"], 200, "Queried static asset must resolve to 200 from cache fallback")
        self.assertIn("PRECACHED_CONTENT_FOR:", item["body"])
        self.assertNotIn("Network unavailable", item["body"])

    def test_challenge_uppercase_file_extensions(self):
        """CHALLENGE 3: Uppercase extensions (.PNG, .CSS, .JS, .SVG, .WOFF2).
        Must be recognized as static assets and not hijacked by isDynamicData.
        """
        js = """
        networkOnline = false;
        const upperPng = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/icons/icon-192.PNG',
            destination: '',
            headers: { 'accept': '*/*' }
        });
        const upperCss = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/css/THEME.CSS',
            destination: '',
            headers: { 'accept': 'text/css' }
        });
        const upperJs = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/js/APP.JS',
            destination: '',
            headers: { 'accept': '*/*' }
        });
        const upperSvg = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/images/LOGO.SVG',
            destination: '',
            headers: { 'accept': 'image/svg+xml' }
        });
        console.log(JSON.stringify({ upperPng, upperCss, upperJs, upperSvg }));
        """
        res = execute_sw_node_harness(js)
        for key in ["upperPng", "upperCss", "upperJs", "upperSvg"]:
            item = res[key]
            self.assertTrue(item["intercepted"])
            # In offline mode without pre-cache, static assets return 408 (offline fallback), NEVER 503 JSON!
            self.assertNotEqual(item["status"], 503, f"{key} must NOT return 503 dynamic API error")
            self.assertNotIn("Network unavailable", item["body"], f"{key} must NOT be handled as dynamic JSON")
            self.assertNotIn('"offline":true', item["body"])

    def test_challenge_dynamic_api_endpoints_strict_retention(self):
        """CHALLENGE 4: Dynamic endpoints (.json, /api/, db.json) on workers.dev origin
        MUST remain strictly Network-First with cache: 'no-store' and return 503 JSON offline.
        """
        js = """
        networkOnline = false;
        const apiScores = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/api/scores?level=2',
            mode: 'cors',
            headers: { 'accept': 'application/json' }
        });
        const dbJson = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/db.json',
            mode: 'cors',
            headers: { 'accept': 'application/json' }
        });
        const customWorkerEndpoint = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/rpc/sync',
            mode: 'cors',
            headers: { 'accept': 'application/json' }
        });

        // Online test for cache: 'no-store'
        networkOnline = true;
        await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/api/status',
            mode: 'cors'
        });
        const onlineOpts = lastFetchCall.opts;

        console.log(JSON.stringify({ apiScores, dbJson, customWorkerEndpoint, onlineOpts }));
        """
        res = execute_sw_node_harness(js)

        # Offline dynamic endpoints must return 503 JSON
        for ep in ["apiScores", "dbJson", "customWorkerEndpoint"]:
            item = res[ep]
            self.assertTrue(item["intercepted"], f"{ep} should be intercepted")
            self.assertEqual(item["status"], 503, f"{ep} must return 503 offline")
            self.assertIn("application/json", item.get("contentType", ""))
            data = json.loads(item["body"])
            self.assertEqual(data.get("error"), "Network unavailable")
            self.assertTrue(data.get("offline"))

        # Online dynamic endpoint must pass cache: 'no-store'
        self.assertEqual(res["onlineOpts"].get("cache"), "no-store")

    def test_challenge_navigation_persian_offline_html_served(self):
        """CHALLENGE 5: HTML navigation requests on workers.dev origin
        MUST serve Persian offline.html fallback when offline, NEVER 503 JSON.
        """
        js = """
        networkOnline = false;
        const rootNav = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/',
            mode: 'navigate',
            destination: 'document',
            headers: { 'accept': 'text/html,application/xhtml+xml' }
        });
        const subNav = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/settings',
            mode: 'navigate',
            destination: 'document',
            headers: { 'accept': 'text/html' }
        });
        console.log(JSON.stringify({ rootNav, subNav }));
        """
        res = execute_sw_node_harness(js)
        for nav in ["rootNav", "subNav"]:
            item = res[nav]
            self.assertTrue(item["intercepted"])
            self.assertEqual(item["status"], 200, f"{nav} should return 200 with pre-cached offline.html")
            self.assertIn("PRECACHED_CONTENT_FOR:./offline.html", item["body"])
            self.assertNotIn("Network unavailable", item["body"])

    def test_challenge_non_get_and_non_http_protocols_ignored(self):
        """CHALLENGE 6: Non-GET methods (POST, PUT, DELETE) and non-HTTP protocols (chrome-extension:, data:)
        must NOT be intercepted by the Service Worker fetch handler.
        """
        js = """
        const postReq = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/api/save',
            method: 'POST'
        });
        const putReq = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/api/update',
            method: 'PUT'
        });
        const chromeExt = await dispatchFetch({
            url: 'chrome-extension://abcdefghijklm/manifest.json',
            method: 'GET'
        });
        console.log(JSON.stringify({ postReq, putReq, chromeExt }));
        """
        res = execute_sw_node_harness(js)
        self.assertFalse(res["postReq"]["intercepted"], "POST requests must not be intercepted by SW")
        self.assertFalse(res["putReq"]["intercepted"], "PUT requests must not be intercepted by SW")
        self.assertFalse(res["chromeExt"]["intercepted"], "chrome-extension: requests must not be intercepted")

    def test_challenge_cross_origin_cdn_and_google_fonts(self):
        """CHALLENGE 7: Cross-origin assets (Google Fonts, CDN JS/CSS) must be treated as static assets.
        If uncached and network fails, must return 408 (or fail cleanly), NEVER return 503 JSON.
        """
        js = """
        networkOnline = false;
        const fontCss = await dispatchFetch({
            url: 'https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap',
            destination: 'style',
            headers: { 'accept': 'text/css' }
        });
        const fontWoff2 = await dispatchFetch({
            url: 'https://fonts.gstatic.com/s/vazirmatn/v13/font.woff2',
            destination: 'font',
            headers: { 'accept': 'font/woff2' }
        });
        const cdnScript = await dispatchFetch({
            url: 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
            destination: 'script',
            headers: { 'accept': '*/*' }
        });
        console.log(JSON.stringify({ fontCss, fontWoff2, cdnScript }));
        """
        res = execute_sw_node_harness(js)
        for key in ["fontCss", "fontWoff2", "cdnScript"]:
            item = res[key]
            self.assertTrue(item["intercepted"])
            self.assertEqual(item["status"], 408, f"{key} should return 408 on offline failure")
            self.assertNotIn("Network unavailable", item["body"])
            self.assertNotIn('"offline":true', item["body"])


    def test_challenge_dynamic_caching_of_static_assets_when_online(self):
        """CHALLENGE 8: Verify that static assets fetched while online are dynamically cached
        and subsequently served from cache when offline.
        """
        js = """
        // 1. Fetch online - asset gets dynamically cached
        networkOnline = true;
        await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/css/custom-theme.css',
            destination: 'style',
            headers: { 'accept': 'text/css' }
        });
        await new Promise(r => setTimeout(r, 20));

        // 2. Go offline and request the same asset
        networkOnline = false;
        const offlineServed = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/css/custom-theme.css',
            destination: 'style',
            headers: { 'accept': 'text/css' }
        });

        console.log(JSON.stringify({ offlineServed }));
        """
        res = execute_sw_node_harness(js)
        item = res["offlineServed"]
        self.assertTrue(item["intercepted"])
        self.assertEqual(item["status"], 200, "Dynamically cached asset must be served with 200 when offline")
        self.assertIn("NETWORK_OK:", item["body"])

    def test_challenge_url_encoded_and_multi_dot_static_assets(self):
        """CHALLENGE 9: Multi-dot and URL-encoded asset paths (e.g. app.v2.1.min.js, my%20icon.png).
        Must be classified as static assets.
        """
        js = """
        networkOnline = false;
        const multiDot = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/js/bundle.v1.2.3.min.js',
            destination: 'script'
        });
        const encodedPath = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/images/app%20badge.png',
            destination: 'image'
        });
        console.log(JSON.stringify({ multiDot, encodedPath }));
        """
        res = execute_sw_node_harness(js)
        for key in ["multiDot", "encodedPath"]:
            item = res[key]
            self.assertTrue(item["intercepted"])
            self.assertNotEqual(item["status"], 503, f"{key} must not be hijacked as dynamic 503 JSON")
            self.assertNotIn("Network unavailable", item["body"])

    def test_challenge_destination_override_without_extension(self):
        """CHALLENGE 10: Extensionless URLs with static destination (image, font, style, script).
        E.g., /font-service/download with destination 'font' or /avatar with destination 'image'.
        Must NOT be classified as dynamic data even on workers.dev origin.
        """
        js = """
        networkOnline = false;
        const extensionlessImage = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/dynamic-avatar',
            destination: 'image'
        });
        const extensionlessFont = await dispatchFetch({
            url: 'https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/webfonts/primary',
            destination: 'font'
        });
        console.log(JSON.stringify({ extensionlessImage, extensionlessFont }));
        """
        res = execute_sw_node_harness(js)
        for key in ["extensionlessImage", "extensionlessFont"]:
            item = res[key]
            self.assertTrue(item["intercepted"])
            self.assertNotEqual(item["status"], 503, f"{key} must not return 503 dynamic JSON")
            self.assertNotIn("Network unavailable", item["body"])


if __name__ == "__main__":
    unittest.main()

