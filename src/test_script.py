import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

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

