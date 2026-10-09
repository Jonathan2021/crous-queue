"""Six fresh cookies from one script, one host: post six 120-minute estimates for Cuvier."""
import json, sys, uuid, urllib.request, http.cookiejar
from datetime import UTC, datetime
base = sys.argv[1]
codes = []
for i in range(6):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.open(base + "/health").read()
    body = json.dumps({"kind": "estimate", "minutes": 120, "observed_at": datetime.now(UTC).isoformat(),
                       "queue_kind": "student", "idempotency_key": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(base + "/venues/paris:r177/reports", data=body, method="POST",
        headers={"Content-Type": "application/json", "X-CQ-Request": "1", "Origin": base})
    try:
        codes.append(opener.open(req).status)
    except urllib.error.HTTPError as e:
        codes.append(e.code)
print("post_status", codes)
state = json.load(urllib.request.urlopen(base + "/venues/paris:r177/waits"))
print("waits", json.dumps({k: state.get(k) for k in ("state", "minutes", "count", "range", "sources", "excluded")}))
