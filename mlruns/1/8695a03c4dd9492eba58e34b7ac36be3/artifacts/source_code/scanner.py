import os
from pathlib import Path

class LocalScanner:
    def __init__(self, root_dir: str, extensions: list[str] = [".py"]):
        self.root_dir = Path(root_dir)
        self.extensions = extensions

    def get_files(self) -> list[str]:
        """Scans local directory for source files."""
        file_list = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if any(file.endswith(ext) for ext in self.extensions):
                    file_list.append(os.path.abspath(os.path.join(root, file)))
        return file_list