import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

class LocalScanner:
    def __init__(self, root_dir: str, extensions: list[str] = [".py", ".json"]):
        self.root_dir = Path(root_dir)
        self.extensions = extensions

    def get_files(self) -> list[str]:
        """Scans local directory for source files and metadata."""
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
        self.extensions = ['.py', '.json'] 

    def scan_remote_folder(self, owner, repo, path, branch="develop"):
        """
        Recursively scans a GitHub folder for source files and DocType metadata.
        """
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            if response.status_code != 200:
                print(f"❌ Failed to access {path}: {response.status_code}")
                return []
            
            items = response.json()
        except Exception as e:
            print(f"⚠️ API Error at {path}: {e}")
            return []

        file_list = []

        for item in items:
            if item['type'] == 'dir':
                # Recursive scan for subdirectories (common in complex DocTypes)
                sub_files = self.scan_remote_folder(owner, repo, item['path'], branch)
                file_list.extend(sub_files)
                
            elif item['type'] == 'file':
                # Check against target extensions
                if any(item['name'].endswith(ext) for ext in self.extensions):
                    file_list.append({
                        "path": item['path'],
                        "download_url": item['download_url'],
                        "type": "metadata" if item['name'].endswith('.json') else "source"
                    })
        
        return file_list