# -*- coding: utf-8 -*-
import json
import re

with open('db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

post_map = {p['id']: p for p in db['posts']}

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "function getInitialSeedDatabase()"
end_marker = "const adminAuditLogs = ["

idx_start = content.find(start_marker)
idx_end = content.find(end_marker, idx_start)

if idx_start == -1 or idx_end == -1:
    print("Could not find getInitialSeedDatabase bounds")
    exit(1)

seed_block = content[idx_start:idx_end]

def replace_post_fields(match):
    post_text = match.group(0)
    pid_m = re.search(r"id:\s*['\"](post-\d+)['\"]", post_text)
    if not pid_m:
        return post_text
    pid = pid_m.group(1)
    if pid not in post_map:
        return post_text
    
    db_post = post_map[pid]
    a_hash = db_post.get('aparatHash', '')
    v_url = db_post.get('videoUrl', '')
    v_subs = db_post.get('videoSubtitles', '')
    
    # Replace aparatHash: '...'
    post_text = re.sub(r"aparatHash:\s*['\"][^'\"]*['\"]", f"aparatHash: '{a_hash}'", post_text)
    # Replace videoUrl: '...'
    post_text = re.sub(r"videoUrl:\s*['\"][^'\"]*['\"]", f"videoUrl: '{v_url}'", post_text)
    # Replace videoSubtitles: '...'
    # Escape single quotes in subtitles if any
    safe_subs = v_subs.replace("'", "\\'")
    post_text = re.sub(r"videoSubtitles:\s*['\"][^'\"]*['\"]", f"videoSubtitles: '{safe_subs}'", post_text)
    return post_text

# Regex for each post object in posts = [ ... ]
pattern = re.compile(r"\{\s*id:\s*['\"]post-\d+['\"].*?attachments:\s*\[", re.DOTALL)
new_seed_block = pattern.sub(replace_post_fields, seed_block)

new_content = content[:idx_start] + new_seed_block + content[idx_end:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated seed posts in index.html successfully.")
