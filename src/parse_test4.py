import re
text = """[Speaker 1]
Hello world.
[Speaker 2]
Hi!"""
pattern = r'(?m)(?:^|\s)\[([^\]]+)\]\s*'
parts = re.split(pattern, text)
print(parts)
