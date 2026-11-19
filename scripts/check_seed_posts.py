import re

content = open('index.html', encoding='utf-8').read()
start_pos = content.find('function getInitialSeedDatabase()')
end_pos = content.find('return {', start_pos)
seed_code = content[start_pos:end_pos]

post_matches = re.findall(r'id:\s*[\'\"](post-\d+)[\'\"]', seed_code)
print(f"Posts in getInitialSeedDatabase: {len(post_matches)}")
print(f"Post IDs: {post_matches}")
