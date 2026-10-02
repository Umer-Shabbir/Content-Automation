import re
import os
from typing import Optional

RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

def sanitize_windows_filename(filename: str, fallback: str = "output", max_length: int = 120) -> str:
    """
    Sanitize a string to be safe for use as a filename on Windows.
    Strips invalid characters, handles reserved names, and truncates length.
    """
    if not filename:
        return fallback

    # Remove path separators to prevent directory traversal
    filename = filename.replace("/", "").replace("\\", "")
    
    # Strip invalid Windows characters: < > : " / \ | ? *
    # Also strip control characters (0-31)
    clean_name = re.sub(r'[<>:"/\|?*\x00-\x1f]', "", filename)
    
    # Strip leading/trailing spaces and dots
    clean_name = clean_name.strip(" .")
    
    # Check for empty after sanitization
    if not clean_name:
        return fallback
        
    # Check for reserved names
    # Need to check the base name without extension
    base = clean_name.split('.')[0].upper()
    if base in RESERVED_NAMES:
        clean_name = f"{clean_name}_safename"
        
    # Truncate to max length, ensuring we don't end in spaces or dots
    if len(clean_name) > max_length:
        clean_name = clean_name[:max_length].strip(" .")
        
    return clean_name or fallback

def sanitize_filename(filename: str, max_length: int = 120) -> str:
    """
    Standard function required by storage specs.
    """
    return sanitize_windows_filename(filename, fallback="untitled", max_length=max_length)

def sanitize_path(path: str) -> str:
    """
    Ensure a path is safe and doesn't contain directory traversal attempts
    like '../' or absolute paths where they aren't expected.
    """
    normalized = os.path.normpath(path)
    
    # Check for directory traversal attempts
    if ".." in normalized.split(os.sep):
        raise ValueError("Directory traversal attempt detected in path")
        
    return normalized
