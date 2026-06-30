import requests, json

BASE = 'http://127.0.0.1:8010'
path = r'D:\AI Data Analyst Agent\localdata\data\samples\sample_sales.csv'

# 1. Health check
h = requests.get(f'{BASE}/health', timeout=10).json()
print(f'[1] Health: {h["status"]} | Model: {h.get("model")}')
assert h['status'] == 'ok'

# 2. Template: Summary
with open(path, 'rb') as f:
    r = requests.post(f'{BASE}/analyze', files={'file': f}, data={'analysis_type': 'summary'}, timeout=120)
d = r.json()
print(f'[2] Template-Summary: status={r.status_code} success={d.get("success")} rows={d.get("rows")} fields={d.get("fields_count")}')
assert r.status_code == 200 and d.get('success')

# 3. Template: Missing/Outliers
with open(path, 'rb') as f:
    r = requests.post(f'{BASE}/analyze', files={'file': f}, data={'analysis_type': 'missing_outliers'}, timeout=120)
d = r.json()
print(f'[3] Template-MissingOutliers: status={r.status_code} success={d.get("success")}')
assert r.status_code == 200 and d.get('success')

# 4. Template: Best/Worst
with open(path, 'rb') as f:
    r = requests.post(f'{BASE}/analyze', files={'file': f}, data={'analysis_type': 'best_worst', 'target_column': 'quantity', 'n': 5}, timeout=120)
d = r.json()
print(f'[4] Template-BestWorst: status={r.status_code} success={d.get("success")} steps={len(d.get("steps",[]))}')
assert r.status_code == 200 and d.get('success')

# 5. Template: Basic Chart
with open(path, 'rb') as f:
    r = requests.post(f'{BASE}/analyze', files={'file': f}, data={'analysis_type': 'basic_chart'}, timeout=120)
d = r.json()
print(f'[5] Template-Chart: status={r.status_code} success={d.get("success")} has_chart={"chart" in d}')
assert r.status_code == 200 and d.get('success')
chart_info = d.get('chart', {})
print(f'  Chart type={chart_info.get("type")} title={chart_info.get("title")} x_len={len(chart_info.get("x",[]))}')

# 6. Agent: Natural language
with open(path, 'rb') as f:
    r = requests.post(f'{BASE}/agent/analyze', files={'file': f}, data={'question': 'What are the top 5 products by revenue?'}, timeout=180)
d = r.json()
print(f'[6] Agent-NL: status={r.status_code} success={d.get("success")} types={d.get("selected_analysis_types")}')
assert r.status_code == 200 and d.get('success')
fa = d.get('final_answer', '') or ''
print(f'  Final answer: {fa[:300]}')

print()
print('=== ALL MANUAL TESTS PASSED ===')
