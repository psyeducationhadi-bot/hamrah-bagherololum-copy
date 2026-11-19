import json

with open('db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

posts = db['posts']
print(f"Total posts: {len(posts)}")
valid = [p for p in posts if p.get('aparatHash') and p.get('videoUrl') and p.get('videoSubtitles')]
print(f"Posts with valid Aparat video & subtitles: {len(valid)} / {len(posts)}")

# Print sample 3 posts
for p in posts[:3]:
    print(f"- {p['id']}: {p['title']}")
    print(f"  Hash: {p['aparatHash']}")
    print(f"  URL:  {p['videoUrl']}")
    print(f"  Subs: {p['videoSubtitles']}")
