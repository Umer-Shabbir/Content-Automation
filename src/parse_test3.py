import re
text = "[af_heart] Hello, how are you? [bm_george] I am fine, thank you! [af_kore] What about you?"
pattern = r'(?:^|\s+)\[([^\]]+)\]\s*'
parts = re.split(pattern, text)
print(parts)
