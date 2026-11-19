import json

with open('db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

for p in db['posts']:
    print(f"{p['id']} | {p['categoryId']} | {p.get('contentType')} | {p['title']}")
