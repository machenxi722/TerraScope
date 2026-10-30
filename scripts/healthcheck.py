import json
import sys
import urllib.request

base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
with urllib.request.urlopen(base + "/api/v1/health", timeout=10) as response:
    print(json.dumps(json.load(response), ensure_ascii=False))
