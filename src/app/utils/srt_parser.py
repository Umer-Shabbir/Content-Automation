import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class SRTChunk:
    index: int
    start_time: str
    end_time: str
    text: str

    def to_dict(self):
        return {
            "index": self.index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text
        }

    def to_xml(self):
        """Converts chunk to an XML representation for LLM ingestion."""
        return f'<chunk index="{self.index}" start_time="{self.start_time}" end_time="{self.end_time}">{self.text}</chunk>'

class SRTParser:
    """
    Parses a standardized SRT file into a list of structured text chunks
    with their corresponding timestamps.
    """

    # Matches SRT timestamp lines like: 00:00:01,000 --> 00:00:04,500 or with dot separators
    TIMESTAMP_REGEX = re.compile(r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})")

    @classmethod
    def parse(cls, srt_content: str) -> List[SRTChunk]:
        """
        Parses raw SRT content into SRTChunk objects.
        """
        chunks = []
        # Split by double newlines considering varying OS line endings
        blocks = re.split(r'\r?\n\r?\n', srt_content.strip())

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # SRT format:
                # 1
                # 00:00:00,000 --> 00:00:03,450
                # Hello world.
                try:
                    index = int(lines[0].strip())
                    time_line = lines[1].strip()

                    text_lines = []
                    for line in lines[2:]:
                        if line.strip():
                            text_lines.append(line.strip())

                    text = " ".join(text_lines)

                    match = cls.TIMESTAMP_REGEX.search(time_line)
                    if match:
                        start_time = match.group(1)
                        end_time = match.group(2)

                        chunks.append(SRTChunk(
                            index=index,
                            start_time=start_time,
                            end_time=end_time,
                            text=text
                        ))
                except Exception as e:
                    # Best effort parsing, skip malformed blocks
                    continue

        return chunks
