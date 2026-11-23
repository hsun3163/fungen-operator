"""Use the image's native HTS tools for the legacy benchmark test constant."""
from pathlib import Path
import shutil


def pytest_collection_modifyitems(items):
    for item in items:
        module = item.module
        if module.__name__ == "test_mws01" and shutil.which("bgzip"):
            module.BIN = Path(shutil.which("bgzip")).parent
