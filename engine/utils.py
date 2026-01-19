import re

def parse_github_url(url: str):
    """
    Parses a GitHub web URL into API components.
    Logic: Uses Regular Expressions (Regex) to find patterns in the string.
    """
    # This pattern looks for the owner, repo, branch, and folder path
    pattern = r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)"
    match = re.match(pattern, url)
    
    if match:
        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "branch": match.group(3),
            "path": match.group(4)
        }
    
    # Fallback for root repository URLs
    return None

# Example Test:
# url = "https://github.com/frappe/erpnext/tree/develop/erpnext/accounts/doctype/sales_invoice"
# print(parse_github_url(url))