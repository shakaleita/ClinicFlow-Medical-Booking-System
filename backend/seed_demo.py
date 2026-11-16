"""Insert optional synthetic demonstration records (safe to rerun)."""
from fastapi.testclient import TestClient
from main import app

SEEDS = [{'patient': 'Alice Example', 'doctor': 'Dr Morgan', 'day': '2026-12-07', 'time': '09:30', 'reason': 'Routine appointment'}, {'patient': 'Bob Example', 'doctor': 'Dr Morgan', 'day': '2026-12-07', 'time': '10:00', 'reason': 'Follow-up'}]
client=TestClient(app)
if client.get('/api/items').json():
    print('Existing records found; skipping seed.')
else:
    for record in SEEDS:
        result=client.post('/api/items',json=record)
        result.raise_for_status()
    print('Added',len(SEEDS),'synthetic sample records.')
