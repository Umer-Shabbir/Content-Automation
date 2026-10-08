import re
text = "Some text without tags. [Speaker A] Hello there! [Speaker B] General Kenobi."
pattern = r'(?:^|\s)\[([^\]]+)\]\s*'
parts = re.split(pattern, text)
print(parts)
