"""Poll /health synchronously until ready=true or timeout."""
import sys
import time
import urllib.request

DEADLINE = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
t0 = time.time()
while time.time() - t0 < DEADLINE:
    try:
        body = urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=2).read().decode()
        if '"ready":true' in body.replace(" ", ""):
            print(f"READY at {time.time()-t0:.1f}s: {body}")
            sys.exit(0)
    except Exception:
        pass
    print(f"[+{time.time()-t0:.0f}s] waiting...", flush=True)
    time.sleep(5)
print("TIMEOUT after", DEADLINE, "s")
sys.exit(1)
