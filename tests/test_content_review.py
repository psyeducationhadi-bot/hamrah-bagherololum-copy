"""Guard against reinstating the high-risk legacy examples in revised seed data."""
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

class TestContentReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = json.loads((ROOT / 'db.json').read_text(encoding='utf-8'))
        cls.posts = {p['id']: p for p in cls.db['posts']}
        cls.faqs = {p['id']: p for p in cls.db['faqs']}
        cls.seed = (ROOT / 'index.html').read_text(encoding='utf-8')
    def test_revised_sleep_and_learning(self):
        self.assertIn('۸ تا ۱۰ ساعت', self.posts['post-8']['content'])
        self.assertNotIn('۷ الی ۷.۵', self.posts['post-8']['content'])
        self.assertNotIn('بیش از ۷۰٪', self.posts['post-11']['content'])
        for post_id in ('post-1','post-4','post-5','post-6','post-7','post-8','post-11','post-12'):
            post = self.posts[post_id]
            self.assertIn('نیازمند تأیید مدرسه', post['author'])
            self.assertIn('نسخه قبلی', post['approvedBy'])
            self.assertEqual(post['version'], 2)
            self.assertIn(post['title'], self.seed)
    def test_legacy_faq_and_categories(self):
        self.assertNotIn('۸ تا ۱۰.۵ ساعت', self.faqs['faq-1']['answer'])
        self.assertNotIn('۷۵ تا ۸۰ درصد', self.faqs['faq-6']['answer'])
        categories = {c['id']: c for c in self.db['categories']}
        self.assertNotIn('نوبت‌های کنکور اردیبهشت و تیر', categories['cat-8']['description'])
        self.assertEqual(next(s['title'] for s in categories['cat-8']['subcategories'] if s['id']=='sub-8-3'), 'برنامه‌ریزی کنکور بر اساس تقویم رسمی')

if __name__ == '__main__':
    unittest.main()
