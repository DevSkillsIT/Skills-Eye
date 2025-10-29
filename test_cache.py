import time
import requests

for i in range(3):
    start = time.time()
    r = requests.get('http://localhost:5000/api/v1/metadata-fields/servers', timeout=10)
    elapsed = time.time() - start
    print(f'Attempt {i+1}: {elapsed:.2f}s - Status: {r.status_code}')
    time.sleep(0.5)
