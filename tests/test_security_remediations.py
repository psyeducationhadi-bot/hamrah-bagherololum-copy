import unittest
import re

INDEX_PATH = r"C:\Users\Pasargad\.gemini\antigravity\scratch\hamrah-bagherololum-copy\index.html"

class TestSecurityRemediations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_showtoast_uses_textcontent_not_raw_innerhtml_message(self):
        # showToast must assign message to textContent to prevent XSS
        self.assertIn("msgSpan.textContent = String(message || '');", self.content)
        self.assertNotIn("el.innerHTML = `<span>${message}</span>", self.content)

    def test_openmodal_sanitizes_script_tags(self):
        # openModal must strip script tags
        self.assertIn("safeHtml.replace(/<script", self.content)
        self.assertIn("safeHtml.replace(/href\\s*=\\s*(['\"])javascript:", self.content)

    def test_syncdatabase_preserves_draft_attachments(self):
        # syncDatabase must use activePosts (status !== 'trash') instead of only publishedPosts for attachments
        self.assertIn("const activePosts = (db.posts || []).filter(p => p.status !== 'trash');", self.content)
        self.assertIn("p.status === 'trash'", self.content)
        self.assertIn("seenAttIds.add(att.id);", self.content)

    def test_url_token_removal_from_href(self):
        # Config modal links must NOT embed admin_token in the href attributes
        self.assertNotIn("workers.dev/#admin_token=${encodeURIComponent(curToken)}", self.content)
        self.assertNotIn("github.io/hamrah-bagherololum-copy/#admin_token=${encodeURIComponent(curToken)}", self.content)
        self.assertIn("📋 کپی کلید دسترسی به کلیپ‌بورد", self.content)

    def test_token_listener_ignores_query_params(self):
        # Must not read admin_token from window.location.search
        self.assertNotIn("params.get('admin_token')", self.content)
        self.assertIn("Security Hardening: Do NOT accept token via URL query (?admin_token=...)", self.content)

    def test_fileupload_strict_magic_bytes_and_payload_scanning(self):
        # Must check JPEG/PNG/GIF/PDF magic bytes and dangerous script payloads
        self.assertIn("JPEG Magic Bytes", self.content)
        self.assertIn("امضای باینری معتبر تصویر PNG است", self.content)
        self.assertIn("textPreview.includes(pat)", self.content)
        self.assertIn("dotParts.length > 2", self.content)

if __name__ == "__main__":
    unittest.main()
