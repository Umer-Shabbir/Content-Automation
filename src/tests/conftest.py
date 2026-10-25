import os

def pytest_sessionfinish(session, exitstatus):
    """
    On Windows with PySide6/Qt, C-runtime shutdown of static Qt objects
    can cause STATUS_STACK_BUFFER_OVERRUN (0xC0000409) after successful test runs.
    Cleanly exit immediately with the actual exit status.
    """
    if os.name == "nt" and exitstatus == 0:
        os._exit(0)
