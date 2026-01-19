import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

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

class GitHubScanner:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {"Authorization": f"token {self.token}"} if self.token else {}
        self.extensions = ['.py','json'] 

    def scan_remote_folder(self, owner, repo, path, branch="develop"):
        """
        Recursively scans a GitHub folder for source files.
        Logic: Uses a GET request to GitHub's 'contents' endpoint.
        """
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        response = requests.get(api_url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to access {path}: {response.status_code}")
            return []

        items = response.json()
        file_list = []

        for item in items:
            if item['type'] == 'dir':
                # RECURSION: If it's a directory, go deeper
                sub_files = self.scan_remote_folder(owner, repo, item['path'], branch)
                file_list.extend(sub_files)
            elif item['type'] == 'file':
                # FILTER: Only keep files with our target extensions
                if any(item['name'].endswith(ext) for ext in self.extensions):
                    # We store the download_url so we can get the code bytes later
                    file_list.append({
                        "path": item['path'],
                        "download_url": item['download_url']
                    })
        
        return file_list
    
# scanner = GitHubScanner()
# files = scanner.scan_remote_folder("frappe", "erpnext", "erpnext/accounts/doctype/sales_invoice")
# print(f"Found {len(files)} files remotely.")