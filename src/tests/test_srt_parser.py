import pytest
from app.utils.srt_parser import SRTParser, SRTChunk

def test_srt_parser_valid_dot():
    srt_content = """1
00:00:01.000 --> 00:00:04.500
Hello world.

2
00:00:05.123 --> 00:00:10.999
This is a test.
"""
    chunks = SRTParser.parse(srt_content)
    assert len(chunks) == 2
    assert chunks[0].start_time == "00:00:01.000"
    assert chunks[0].end_time == "00:00:04.500"
    assert chunks[0].text == "Hello world."
    assert chunks[1].start_time == "00:00:05.123"
    assert chunks[1].end_time == "00:00:10.999"
    assert chunks[1].text == "This is a test."

def test_srt_parser_valid_comma():
    srt_content = """1
00:00:01,000 --> 00:00:04,500
Hello world.

2
00:00:05,123 --> 00:00:10,999
This is a test.
"""
    chunks = SRTParser.parse(srt_content)
    assert len(chunks) == 2
    assert chunks[0].start_time == "00:00:01,000"
    assert chunks[0].end_time == "00:00:04,500"
    assert chunks[0].text == "Hello world."

def test_srt_parser_to_xml():
    chunk = SRTChunk(index=1, start_time="00:00:01,000", end_time="00:00:04,500", text="Hello world.")
    xml = chunk.to_xml()
    assert xml == '<chunk index="1" start_time="00:00:01,000" end_time="00:00:04,500">Hello world.</chunk>'

def test_srt_parser_malformed():
    srt_content = """1
00:00:01,000 --> 00:00:04,500
Hello world.

2
INVALID TIME FORMAT
This is a test.
"""
    chunks = SRTParser.parse(srt_content)
    assert len(chunks) == 1
    assert chunks[0].index == 1
