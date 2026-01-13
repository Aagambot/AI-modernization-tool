import requests
import pathspec
from typing import List, Dict
from pathlib import Path
import re

class RemoteScanner:
    def __init__(self, github_url: str, extensions: List[str] = [".py", ".js", ".java"]):
        """
        Independent file discovery that handles deep links and specific branches.
        """
        self.github_url = github_url.rstrip("/")
        self.extensions = extensions
        self._parse_github_url()
        
        self.ignore_patterns = ["node_modules/", "__pycache__/", ".git/", "tests/", "*.min.js"]
        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', self.ignore_patterns)

    def _parse_github_url(self):
        """Extracts owner, repo, branch, and sub-path from a complex GitHub URL."""
        # Matches: https://github.com/owner/repo/tree/branch/folder_path
        pattern = r"github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)/(.*))?"
        match = re.search(pattern, self.github_url)
        
        if not match:
            raise ValueError("Invalid GitHub URL format.")
            
        self.owner = match.group(1)
        self.repo = match.group(2)
        self.branch = match.group(3) or "main" # Default to main if not specified
        self.sub_path = match.group(4) or ""
        
    def get_file_list(self) -> List[Dict]:
        # Using the recursive tree API for the specific branch
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/{self.branch}?recursive=1"
        
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            tree = response.json().get("tree", [])
        except Exception as e:
            print(f"❌ Error accessing GitHub API: {e}")
            return []

        discovered_files = []
        for item in tree:
            path = item["path"]
            
            # 1. Only process if inside the requested sub_path
            if self.sub_path and not path.startswith(self.sub_path):
                continue

            # 2. Check if it's a file (blob) and matches our extensions
            if item["type"] == "blob" and any(path.endswith(ext) for ext in self.extensions):
                # 3. Check against ignore patterns
                if not self.spec.match_file(path):
                    raw_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{self.branch}/{path}"
                    discovered_files.append({
                        "path": path,
                        "download_url": raw_url,
                        "extension": Path(path).suffix
                    })
        return discovered_files

if __name__ == "__main__":
    # Test with your specific Sales Invoice deep link
    url = "https://github.com/frappe/erpnext/tree/develop/erpnext/accounts/doctype/sales_invoice"
    scanner = RemoteScanner(url, extensions=[".py"])
    
    print(f"🔍 Scanning branch '{scanner.branch}' in {scanner.owner}/{scanner.repo}...")
    print(f"📂 Filtering for path: {scanner.sub_path or 'Root'}")
    
    files = scanner.get_file_list()
    print(f"✅ Found {len(files)} valid source files.")
    
    for f in files[:3]: # Print first 3 to verify
        print(f"📄 {f['path']}")