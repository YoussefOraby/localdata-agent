"""
Starts the backend, runs all manual API tests, and shuts down.
Usage: python _manual_verify.py
"""
import subprocess
import sys
import time
import os

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "data", "samples", "sample_sales.csv")

# Start backend
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8010", "--host", "127.0.0.1"],
    cwd=BACKEND_DIR,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print("Starting backend...")
time.sleep(8)

import requests

BASE = "http://127.0.0.1:8010"
passed = 0
failed = 0

def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  PASS: {name}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {name} -- {e}")
        failed += 1

# 1. Health
def health():
    r = requests.get(f"{BASE}/health", timeout=10).json()
    assert r["status"] == "ok"
    assert "model" in r
test("Health endpoint", health)

# 2. Template: Summary
def template_summary():
    with open(SAMPLE_CSV, "rb") as f:
        r = requests.post(f"{BASE}/analyze", files={"file": f}, data={"analysis_type": "summary"}, timeout=120)
    d = r.json()
    assert r.status_code == 200
    assert d.get("success")
    assert d.get("rows") == 25
test("Template: Summary", template_summary)

# 3. Template: Missing/Outliers
def template_missing():
    with open(SAMPLE_CSV, "rb") as f:
        r = requests.post(f"{BASE}/analyze", files={"file": f}, data={"analysis_type": "missing_outliers"}, timeout=120)
    d = r.json()
    assert r.status_code == 200 and d.get("success")
test("Template: Missing/Outliers", template_missing)

# 4. Template: Best/Worst
def template_bestworst():
    with open(SAMPLE_CSV, "rb") as f:
        r = requests.post(f"{BASE}/analyze", files={"file": f}, data={"analysis_type": "best_worst", "target_column": "quantity", "n": 5}, timeout=120)
    d = r.json()
    assert r.status_code == 200 and d.get("success")
test("Template: Best/Worst", template_bestworst)

# 5. Template: Basic Chart
def template_chart():
    with open(SAMPLE_CSV, "rb") as f:
        r = requests.post(f"{BASE}/analyze", files={"file": f}, data={"analysis_type": "basic_chart"}, timeout=120)
    d = r.json()
    assert r.status_code == 200 and d.get("success")
    assert "chart" in d
test("Template: Basic Chart", template_chart)

# 6. Agent: Summarize
def agent_summarize():
    with open(SAMPLE_CSV, "rb") as f:
        r = requests.post(f"{BASE}/agent/analyze", files={"file": f}, data={"question": "Summarize this dataset."}, timeout=180)
    d = r.json()
    assert r.status_code == 200 and d.get("success")
    assert d.get("selected_analysis_types")
    assert d.get("final_answer")
test("Agent: Summarize", agent_summarize)

# 7. Agent: Missing values
def agent_missing():
    with open(SAMPLE_CSV, "rb") as f:
        r = requests.post(f"{BASE}/agent/analyze", files={"file": f}, data={"question": "Find missing values and outliers."}, timeout=180)
    d = r.json()
    assert r.status_code == 200 and d.get("success")
    assert d.get("selected_analysis_types")
    assert d.get("final_answer")
test("Agent: Missing values & outliers", agent_missing)

# 8. Agent: Combined
def agent_combined():
    with open(SAMPLE_CSV, "rb") as f:
        r = requests.post(f"{BASE}/agent/analyze", files={"file": f}, data={"question": "Summarize this dataset and show missing values."}, timeout=180)
    d = r.json()
    assert r.status_code == 200 and d.get("success")
    types = d.get("selected_analysis_types", [])
    assert "summary" in types
test("Agent: Combined (summary + missing)", agent_combined)

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
print(f"{'='*40}")

# Shutdown
proc.terminate()
proc.wait()
print("Backend shut down.")

sys.exit(0 if failed == 0 else 1)
