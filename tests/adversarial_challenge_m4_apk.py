#!/usr/bin/env python3
"""Milestone 4 Adversarial Challenge & Empirical Integrity Suite.

Author: m4_challenger_1 (Role: critic, specialist)
Objective: Empirically stress-test M4 Android TWA release artifacts:
1. Internal ZIP archive structure of release APK and AAB.
2. Classes.dex, AndroidManifest.xml, resources.arsc, res/, META-INF/.
3. Digital signature verification via official Android apksigner tool (v1 + v2).
4. Adversarial tampering resistance across multiple attack vectors:
   - Byte alteration in classes.dex payload
   - Byte alteration in AndroidManifest.xml payload
   - Byte alteration in APK v2 Signing Block
   - Trailing byte injection (end-of-file contamination)
   - Unauthorized file injection into APK archive
5. Byte-for-byte certificate SHA-256 cross-artifact congruence:
   - android.keystore vs android/app/android.keystore
   - KEYSTORE_CREDENTIALS.txt (text & Base64 decoding)
   - .well-known/assetlinks.json (handle_all_urls & cafebazaar_twa)
   - META-INF/CERT.RSA inside hamrah-bagherololum-release.apk
6. Compiled AndroidManifest and resources.arsc TWA compliance via aapt2.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, pkcs7, pkcs12

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RELEASE_APK = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.apk"
RELEASE_AAB = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.aab"
KEYSTORE_ROOT = PROJECT_ROOT / "android.keystore"
KEYSTORE_APP = PROJECT_ROOT / "android" / "app" / "android.keystore"
KEYSTORE_TXT = PROJECT_ROOT / "KEYSTORE_CREDENTIALS.txt"
ASSETLINKS = PROJECT_ROOT / ".well-known" / "assetlinks.json"

APKSIGNER_BAT = Path(r"C:\Users\Pasargad\AppData\Local\Android\Sdk\build-tools\34.0.0\apksigner.bat")
AAPT2_EXE = Path(r"C:\Users\Pasargad\AppData\Local\Android\Sdk\build-tools\34.0.0\aapt2.exe")

EXPECTED_SHA256 = "F2:11:BF:37:3C:30:60:2D:31:D4:28:32:D2:8A:B7:09:C4:AA:6A:29:6F:F3:01:43:19:2C:17:CA:1C:A4:56:FE"
EXPECTED_PACKAGE = "ir.bagherololum.hamrah"
EXPECTED_KEYSTORE_PASS = b"Hamrah2026Release!"


class TestM4AdversarialApk(unittest.TestCase):
    """Empirical challenge suite for M4 Android TWA artifacts."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(RELEASE_APK.exists(), f"Release APK must exist at {RELEASE_APK}")
        cls.assertTrue(RELEASE_AAB.exists(), f"Release AAB must exist at {RELEASE_AAB}")
        cls.assertTrue(APKSIGNER_BAT.exists(), f"apksigner tool must exist at {APKSIGNER_BAT}")
        cls.assertTrue(AAPT2_EXE.exists(), f"aapt2 tool must exist at {AAPT2_EXE}")

    def test_01_apk_archive_internal_structure(self):
        """CHALLENGE 1: Inspect APK ZIP archive structure and essential components."""
        with zipfile.ZipFile(RELEASE_APK, "r") as z:
            names = z.namelist()

            # 1. classes.dex
            self.assertIn("classes.dex", names, "classes.dex must exist in APK root")
            dex_info = z.getinfo("classes.dex")
            self.assertGreater(dex_info.file_size, 1_000_000, "classes.dex uncompressed size must exceed 1MB")
            dex_data = z.read("classes.dex")
            self.assertTrue(dex_data.startswith(b"dex\n"), "classes.dex must start with DEX magic header ('dex\\n')")

            # 2. AndroidManifest.xml
            self.assertIn("AndroidManifest.xml", names, "AndroidManifest.xml must exist in APK")
            manifest_info = z.getinfo("AndroidManifest.xml")
            self.assertGreater(manifest_info.file_size, 1000, "AndroidManifest.xml size must be > 1000 bytes")

            # 3. resources.arsc
            self.assertIn("resources.arsc", names, "resources.arsc must exist in APK")
            arsc_info = z.getinfo("resources.arsc")
            self.assertGreater(arsc_info.file_size, 10_000, "resources.arsc size must be > 10KB")

            # 4. res/ folder contents
            res_entries = [n for n in names if n.startswith("res/")]
            self.assertGreater(len(res_entries), 50, "res/ directory must contain abundant resources")

            # 5. META-INF/ signature block
            self.assertIn("META-INF/MANIFEST.MF", names, "META-INF/MANIFEST.MF must exist")
            self.assertIn("META-INF/CERT.SF", names, "META-INF/CERT.SF must exist")
            self.assertIn("META-INF/CERT.RSA", names, "META-INF/CERT.RSA must exist")

    def test_02_aab_archive_internal_structure(self):
        """CHALLENGE 2: Inspect AAB ZIP archive structure (bundle modules & metadata)."""
        with zipfile.ZipFile(RELEASE_AAB, "r") as z:
            names = z.namelist()

            # Base module structure
            self.assertIn("base/manifest/AndroidManifest.xml", names, "base/manifest/AndroidManifest.xml must exist")
            self.assertIn("base/dex/classes.dex", names, "base/dex/classes.dex must exist")
            dex_info = z.getinfo("base/dex/classes.dex")
            self.assertGreater(dex_info.file_size, 1_000_000, "AAB base classes.dex must exceed 1MB")

            self.assertIn("base/resources.pb", names, "base/resources.pb protocol buffer resources must exist")
            base_res = [n for n in names if n.startswith("base/res/")]
            self.assertGreater(len(base_res), 50, "base/res/ must contain compiled resources")

            bundle_meta = [n for n in names if n.startswith("BUNDLE-METADATA/")]
            self.assertGreater(len(bundle_meta), 0, "BUNDLE-METADATA/ must exist in AAB")

    def test_03_apksigner_official_verification(self):
        """CHALLENGE 3: Run official apksigner verification tool (v1 + v2 schemes)."""
        cmd = [
            str(APKSIGNER_BAT),
            "verify",
            "--min-sdk-version", "21",
            "--verbose",
            "--print-certs",
            str(RELEASE_APK),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, f"apksigner failed:\n{proc.stderr}\n{proc.stdout}")

        stdout = proc.stdout
        self.assertIn("Verifies", stdout, "apksigner must output 'Verifies'")
        self.assertIn("Verified using v1 scheme (JAR signing): true", stdout)
        self.assertIn("Verified using v2 scheme (APK Signature Scheme v2): true", stdout)
        self.assertIn("Number of signers: 1", stdout)
        self.assertIn("CN=Hamrah Bagherololum", stdout)

        # Normalize digest output
        raw_fp = EXPECTED_SHA256.lower().replace(":", "")
        self.assertIn(raw_fp, stdout.lower().replace(":", ""), "Certificate SHA-256 digest in apksigner must match")

    def test_04_tampering_resistance_dex_payload_alteration(self):
        """CHALLENGE 4 (Hostile Attack): Alter a single byte inside classes.dex payload.
        Verify that apksigner detects chunked SHA-256 digest mismatch and fails verification.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tampered_apk = Path(tmpdir) / "tampered-dex.apk"
            shutil.copy2(RELEASE_APK, tampered_apk)

            with zipfile.ZipFile(RELEASE_APK, "r") as z:
                dex_info = z.getinfo("classes.dex")
                offset = dex_info.header_offset

            with open(tampered_apk, "r+b") as f:
                f.seek(offset + 50)
                b = f.read(1)[0]
                f.seek(offset + 50)
                f.write(bytes([b ^ 0x55]))

            cmd = [str(APKSIGNER_BAT), "verify", "--verbose", str(tampered_apk)]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(proc.returncode, 0, "apksigner MUST fail when classes.dex payload is tampered")
            combined_err = (proc.stderr + proc.stdout).lower()
            self.assertTrue(
                "does not verify" in combined_err and ("integrity" in combined_err or "digest" in combined_err),
                f"apksigner error should mention integrity/digest mismatch. Output: {proc.stderr}\n{proc.stdout}",
            )

    def test_05_tampering_resistance_manifest_payload_alteration(self):
        """CHALLENGE 5 (Hostile Attack): Alter a byte inside AndroidManifest.xml payload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tampered_apk = Path(tmpdir) / "tampered-manifest.apk"
            shutil.copy2(RELEASE_APK, tampered_apk)

            with open(tampered_apk, "r+b") as f:
                content = bytearray(f.read())
                # Search for package name inside compiled manifest in APK
                pos = content.find(b"ir.bagherololum.hamrah")
                self.assertGreater(pos, 0, "Package name string not found in APK binary")
                content[pos + 16] = ord(b"t")
                f.seek(0)
                f.write(content)

            cmd = [str(APKSIGNER_BAT), "verify", str(tampered_apk)]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(proc.returncode, 0, "apksigner MUST fail when AndroidManifest is tampered")

    def test_06_tampering_resistance_signing_block_alteration(self):
        """CHALLENGE 6 (Hostile Attack): Alter a byte inside the APK v2 Signing Block value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tampered_apk = Path(tmpdir) / "tampered-sigblock.apk"
            shutil.copy2(RELEASE_APK, tampered_apk)

            with open(tampered_apk, "r+b") as f:
                content = bytearray(f.read())
                v2_id = struct.pack("<I", 0x7109871A)
                pos_v2 = content.find(v2_id)
                self.assertGreater(pos_v2, 0, "APK Signing Block v2 ID (0x7109871a) not found")
                content[pos_v2 + 30] ^= 0xAA
                f.seek(0)
                f.write(content)

            cmd = [str(APKSIGNER_BAT), "verify", "--verbose", str(tampered_apk)]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(proc.returncode, 0, "apksigner MUST fail when APK Signing Block is corrupted")
            combined_err = (proc.stderr + proc.stdout).lower()
            self.assertTrue(
                "does not verify" in combined_err or "signature" in combined_err,
                f"apksigner error should mention signature verification failure: {proc.stderr}\n{proc.stdout}",
            )

    def test_07_tampering_resistance_trailing_byte_injection(self):
        """CHALLENGE 7 (Hostile Attack): Append trailing byte at the end of APK.
        APK Signature Scheme v2 verifies hashes over whole ZIP chunks, rejecting trailing data.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tampered_apk = Path(tmpdir) / "tampered-trailing.apk"
            shutil.copy2(RELEASE_APK, tampered_apk)

            with open(tampered_apk, "ab") as f:
                f.write(b"\x00\xFF\xDE\xAD\xBE\xEF")

            cmd = [str(APKSIGNER_BAT), "verify", str(tampered_apk)]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(proc.returncode, 0, "apksigner MUST fail when trailing garbage is appended")

    def test_08_tampering_resistance_file_injection(self):
        """CHALLENGE 8 (Hostile Attack): Inject an unauthorized file into the APK ZIP archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tampered_apk = Path(tmpdir) / "tampered-injected.apk"
            shutil.copy2(RELEASE_APK, tampered_apk)

            # Open with zipfile in append mode and inject unauthorized file
            with zipfile.ZipFile(tampered_apk, "a") as z:
                z.writestr("evil_payload.txt", "unauthorized injection attack")

            cmd = [str(APKSIGNER_BAT), "verify", str(tampered_apk)]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(proc.returncode, 0, "apksigner MUST fail when file is injected into signed APK")

    def test_09_certificate_digest_cross_artifact_byte_congruence(self):
        """CHALLENGE 9: Assert certificate SHA-256 fingerprint is 100% byte-for-byte identical across:
        1. android.keystore
        2. android/app/android.keystore
        3. KEYSTORE_CREDENTIALS.txt (text & base64)
        4. .well-known/assetlinks.json
        5. META-INF/CERT.RSA inside the release APK
        """
        # 1. From root android.keystore
        with open(KEYSTORE_ROOT, "rb") as f:
            _, ks_cert, _ = pkcs12.load_key_and_certificates(f.read(), EXPECTED_KEYSTORE_PASS)
        der_root = ks_cert.public_bytes(Encoding.DER)
        fp_root = hashlib.sha256(der_root).hexdigest().upper()
        fp_root_colon = ":".join(fp_root[i:i+2] for i in range(0, len(fp_root), 2))
        self.assertEqual(fp_root_colon, EXPECTED_SHA256, "android.keystore fingerprint mismatch")

        # 2. From android/app/android.keystore
        with open(KEYSTORE_APP, "rb") as f:
            _, app_cert, _ = pkcs12.load_key_and_certificates(f.read(), EXPECTED_KEYSTORE_PASS)
        der_app = app_cert.public_bytes(Encoding.DER)
        self.assertEqual(der_app, der_root, "android.keystore and android/app/android.keystore DER bytes must match")

        # 3. From KEYSTORE_CREDENTIALS.txt
        txt_content = KEYSTORE_TXT.read_text(encoding="utf-8")
        self.assertIn(EXPECTED_SHA256, txt_content, "KEYSTORE_CREDENTIALS.txt must contain authoritative SHA-256")

        # Base64 string in KEYSTORE_CREDENTIALS.txt
        b64_match = re.search(r"MIIK[A-Za-z0-9+/=]+", txt_content)
        self.assertIsNotNone(b64_match, "Base64 keystore string must be present in KEYSTORE_CREDENTIALS.txt")
        b64_bytes = base64.b64decode(b64_match.group(0))
        _, b64_cert, _ = pkcs12.load_key_and_certificates(b64_bytes, EXPECTED_KEYSTORE_PASS)
        der_b64 = b64_cert.public_bytes(Encoding.DER)
        self.assertEqual(der_b64, der_root, "Base64 keystore DER certificate must match root keystore")

        # 4. From .well-known/assetlinks.json
        assetlinks_data = json.loads(ASSETLINKS.read_text(encoding="utf-8"))
        for stmt in assetlinks_data:
            target = stmt.get("target", {})
            self.assertEqual(target.get("package_name"), EXPECTED_PACKAGE)
            fps = target.get("sha256_cert_fingerprints", [])
            self.assertIn(EXPECTED_SHA256, fps, f"Statement {stmt.get('relation')} must contain SHA-256")

        # 5. From META-INF/CERT.RSA inside release APK
        with zipfile.ZipFile(RELEASE_APK, "r") as z:
            rsa_data = z.read("META-INF/CERT.RSA")
        apk_certs = pkcs7.load_der_pkcs7_certificates(rsa_data)
        self.assertEqual(len(apk_certs), 1, "CERT.RSA must contain exactly 1 certificate")
        der_apk = apk_certs[0].public_bytes(Encoding.DER)
        self.assertEqual(der_apk, der_root, "CERT.RSA DER certificate must match keystore certificate")
        fp_apk = hashlib.sha256(der_apk).hexdigest().upper()
        fp_apk_colon = ":".join(fp_apk[i:i+2] for i in range(0, len(fp_apk), 2))
        self.assertEqual(fp_apk_colon, EXPECTED_SHA256, "APK certificate SHA-256 mismatch")

    def test_10_manifest_twa_security_and_bazaar_spec(self):
        """CHALLENGE 10: Inspect compiled AndroidManifest.xml and resources via aapt2."""
        # Check badging
        badging_cmd = [str(AAPT2_EXE), "dump", "badging", str(RELEASE_APK)]
        b_proc = subprocess.run(badging_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(b_proc.returncode, 0)
        badging = b_proc.stdout

        self.assertIn(f"package: name='{EXPECTED_PACKAGE}'", badging)
        self.assertIn("compileSdkVersion='35'", badging)
        self.assertIn("sdkVersion:'24'", badging)
        self.assertIn("targetSdkVersion:'34'", badging)
        self.assertIn("application-label:'همراه باقرالعلوم'", badging)
        self.assertIn("launchable-activity: name='com.google.androidbrowserhelper.trusted.LauncherActivity'", badging)

        # Check AndroidManifest.xml tree
        xml_cmd = [str(AAPT2_EXE), "dump", "xmltree", str(RELEASE_APK), "--file", "AndroidManifest.xml"]
        x_proc = subprocess.run(xml_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(x_proc.returncode, 0)
        xmltree = x_proc.stdout

        self.assertIn("DEFAULT_URL", xmltree)
        self.assertIn("https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app", xmltree)
        self.assertIn("FALLBACK_STRATEGY", xmltree)
        self.assertIn("webview", xmltree)
        self.assertIn("DISPLAY_MODE", xmltree)
        self.assertIn("standalone", xmltree)
        self.assertIn("ADDITIONAL_TRUSTED_ORIGINS", xmltree)
        self.assertIn("FileProvider", xmltree)
        self.assertIn(f"{EXPECTED_PACKAGE}.fileprovider", xmltree)
        self.assertIn("DelegationService", xmltree)
        self.assertIn("TRUSTED_WEB_ACTIVITY_SERVICE", xmltree)

        # Check resources dump for additional_trusted_origins and asset_statements
        res_cmd = [str(AAPT2_EXE), "dump", "resources", str(RELEASE_APK)]
        r_proc = subprocess.run(res_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r_proc.returncode, 0)
        res_out = r_proc.stdout

        self.assertIn("https://psyeducationhadi-bot.github.io", res_out)
        self.assertIn("hamrah-bagherololum-copy.psyeducation-hadi.workers.dev", res_out)
        self.assertIn("cafebazaar_twa", res_out)


if __name__ == "__main__":
    unittest.main()
