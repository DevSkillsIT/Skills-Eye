import requests
import json

API_URL = "http://localhost:5000/api/v1/prometheus-config"

# 1. Get current jobs
print("1. Getting current jobs...")
response = requests.get(f"{API_URL}/file/jobs?file_path=/etc/prometheus/prometheus.yml", timeout=15)
print(f"   Status: {response.status_code}")
if response.status_code != 200:
    print(f"   ERROR: {response.text}")
    exit(1)

data = response.json()
jobs = data.get('jobs', [])
print(f"   Found {len(jobs)} jobs")

# 2. Find the 'mktxp' job (it's a simple static_config job)
mktxp_job = None
for job in jobs:
    if job.get('job_name') == 'mktxp':
        mktxp_job = job
        break

if not mktxp_job:
    print("   ERROR: mktxp job not found")
    exit(1)

print(f"\n2. Found mktxp job:")
print(f"   {json.dumps(mktxp_job, indent=2)}")

# 3. Make a small modification (add a comment field that will be in the JSON)
# Keep the job exactly the same to minimize changes
modified_job = mktxp_job.copy()

# Update the jobs list with the modified job
updated_jobs = []
for job in jobs:
    if job.get('job_name') == 'mktxp':
        updated_jobs.append(modified_job)
    else:
        updated_jobs.append(job)

# 4. Send the update request
print(f"\n3. Sending update request...")
response = requests.put(
    f"{API_URL}/file/jobs?file_path=/etc/prometheus/prometheus.yml",
    json=updated_jobs,
    timeout=30
)

print(f"   Status: {response.status_code}")
print(f"   Response: {response.text}")

if response.status_code == 200:
    print("\n✓ SUCCESS! Job update worked without errors")
else:
    print(f"\n✗ FAILED with status {response.status_code}")
