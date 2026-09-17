import urllib.request
import json

url = 'https://api.github.com/repos/Abhinaykalal/sih/pulls?state=all'
req = urllib.request.Request(url, headers={'User-Agent': 'AgriSaathi/1.0'})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"Total Pull Requests found: {len(data)}")
        for pr in data:
            num = pr.get("number")
            state = pr.get("state", "").upper()
            title = pr.get("title")
            user = pr.get("user", {}).get("login")
            html_url = pr.get("html_url")
            created = pr.get("created_at")
            merged = pr.get("merged_at")
            status_str = f"MERGED" if merged else state
            print(f"#{num} [{status_str}] {title} (by @{user})")
            print(f"   URL: {html_url}")
            print(f"   Created: {created}")
            if merged:
                print(f"   Merged at: {merged}")
            print("-" * 50)
except Exception as e:
    print(f"Error fetching PRs: {e}")
