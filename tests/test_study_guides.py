"""Static checks for the standalone guides and their category links."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent

class GuideParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.hrefs = []
        self.h1 = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a' and 'href' in attrs:
            self.hrefs.append(attrs['href'])
        self.h1 += tag == 'h1'

class TestStudyGuides(unittest.TestCase):
    def test_guide_links_and_structure(self):
        for file in (ROOT / 'guides').glob('*.html'):
            with self.subTest(file=file.name):
                parser = GuideParser()
                parser.feed(file.read_text(encoding='utf-8'))
                self.assertEqual(parser.h1, 1)
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                for href in parser.hrefs:
                    url = urlparse(href)
                    if not url.scheme and not url.netloc:
                        if url.path:
                            self.assertTrue((file.parent / url.path).is_file(), href)
                        elif url.fragment:
                            self.assertIn(url.fragment, parser.ids)
    def test_category_guide_coverage(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        match = re.search(r"const studyGuides = new Set\(\[(.*?)\]\)", html)
        self.assertIsNotNone(match)
        ids = re.findall(r"'([^']+)'", match.group(1))
        data = json.loads((ROOT / 'db.json').read_text(encoding='utf-8'))
        known = {sub['id'] for cat in data['categories'] for sub in cat['subcategories']}
        parser = GuideParser()
        parser.feed((ROOT / 'guides/study-skills.html').read_text(encoding='utf-8'))
        self.assertEqual(len(ids), 8)
        self.assertTrue(set(ids) <= known)
        self.assertTrue(set(ids) <= set(parser.ids))
    def test_exam_guide_coverage(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        match = re.search(r"const examGuides = new Set\(\[(.*?)\]\)", html)
        self.assertIsNotNone(match)
        ids = re.findall(r"'([^']+)'", match.group(1))
        data = json.loads((ROOT / 'db.json').read_text(encoding='utf-8'))
        known = {sub['id'] for cat in data['categories'] for sub in cat['subcategories']}
        parser = GuideParser()
        parser.feed((ROOT / 'guides/exam-preparation.html').read_text(encoding='utf-8'))
        self.assertEqual(len(ids), 12)
        self.assertTrue(set(ids) <= known)
        self.assertTrue(set(ids) <= set(parser.ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_wellbeing_guide_coverage(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        match = re.search(r"const wellbeingGuides = new Set\(\[(.*?)\]\)", html)
        self.assertIsNotNone(match)
        ids = re.findall(r"'([^']+)'", match.group(1))
        data = json.loads((ROOT / 'db.json').read_text(encoding='utf-8'))
        known = {sub['id'] for cat in data['categories'] for sub in cat['subcategories']}
        parser = GuideParser()
        parser.feed((ROOT / 'guides/student-wellbeing.html').read_text(encoding='utf-8'))
        self.assertEqual(len(ids), 12)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(ids) <= known)
        self.assertTrue(set(ids) <= set(parser.ids))

    def test_goals_guide_coverage(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        match = re.search(r"const goalsGuides = new Set\(\[(.*?)\]\)", html)
        self.assertIsNotNone(match)
        ids = re.findall(r"'([^']+)'", match.group(1))
        data = json.loads((ROOT / 'db.json').read_text(encoding='utf-8'))
        known = {sub['id'] for cat in data['categories'] for sub in cat['subcategories']}
        parser = GuideParser()
        parser.feed((ROOT / 'guides/goals-relationships.html').read_text(encoding='utf-8'))
        self.assertEqual(len(ids), 11)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(ids) <= known)
        self.assertTrue(set(ids) <= set(parser.ids))

    def test_complete_subcategory_coverage(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        data = json.loads((ROOT / 'db.json').read_text(encoding='utf-8'))
        known = {sub['id'] for cat in data['categories'] for sub in cat['subcategories']}
        groups = {'studyGuides': 'study-skills.html', 'examGuides': 'exam-preparation.html',
                  'wellbeingGuides': 'student-wellbeing.html', 'goalsGuides': 'goals-relationships.html',
                  'futureGuides': 'future-and-faq.html'}
        covered = []
        for name, filename in groups.items():
            match = re.search(r"const " + name + r" = new Set\(\[(.*?)\]\)", html)
            self.assertIsNotNone(match, name)
            ids = re.findall(r"'([^']+)'", match.group(1))
            parser = GuideParser()
            parser.feed((ROOT / 'guides' / filename).read_text(encoding='utf-8'))
            self.assertTrue(set(ids) <= set(parser.ids), name)
            covered.extend(ids)
        self.assertEqual(len(covered), len(set(covered)))
        self.assertEqual(set(covered), known)
        self.assertIn("subId: parts[2] || ''", html)
        self.assertIn('aria-label="زیرموضوع‌ها"', html)

    def test_cross_guide_anchors(self):
        for file in (ROOT / 'guides').glob('*.html'):
            parser = GuideParser()
            parser.feed(file.read_text(encoding='utf-8'))
            for href in parser.hrefs:
                url = urlparse(href)
                if not url.scheme and url.path.endswith('.html') and url.fragment and not url.fragment.startswith('/'):
                    target = file.parent / url.path
                    other = GuideParser()
                    other.feed(target.read_text(encoding='utf-8'))
                    self.assertIn(url.fragment, other.ids, href)

    def test_sitemap(self):
        root = ET.parse(ROOT / 'sitemap.xml').getroot()
        locations = [x.text for x in root.findall('{*}url/{*}loc')]
        self.assertTrue(any(x.endswith('/guides/study-skills.html') for x in locations))
        self.assertTrue(any(x.endswith('/guides/exam-preparation.html') for x in locations))
        self.assertTrue(any(x.endswith('/guides/student-wellbeing.html') for x in locations))
        self.assertTrue(any(x.endswith('/guides/goals-relationships.html') for x in locations))
        self.assertTrue(any(x.endswith('/guides/future-and-faq.html') for x in locations))

if __name__ == '__main__':
    unittest.main()
