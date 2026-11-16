import importlib,os,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temp = tempfile.mkdtemp(prefix='portfolio-test-')
os.environ['APP_DB']=str(Path(temp)/'test.db')
os.environ['OWNER_SETUP_TOKEN']='test-only-setup-token-1234567890123'
if 'main' in sys.modules: del sys.modules['main']
from main import app
client=TestClient(app)
assert client.post('/api/auth/register',json={'username':'qaowner','password':'DemoPassword123!','setup_token':'test-only-setup-token-1234567890123'}).status_code==201
assert client.post('/api/auth/login',json={'username':'qaowner','password':'DemoPassword123!'}).status_code==200

def test_health():
    r=client.get('/api/health')
    assert r.status_code==200 and r.json()['ok']

def test_initial_list():
    r=client.get('/api/items')
    assert r.status_code==200 and isinstance(r.json(),list)

def test_summary():
    r=client.get('/api/summary')
    assert r.status_code==200 and isinstance(r.json(),list)


# v0.3 regression tests
def test_appointment_availability_and_reschedule():
    body={'patient':'Synthetic Patient','doctor':'Dr QA','day':'2030-01-12','time':'10:00','reason':'Demo'}
    a=client.post('/api/items',json=body)
    assert a.status_code==201
    b=client.post('/api/items',json={**body,'patient':'Another Demo'})
    assert b.status_code==409
    avail=client.get('/api/availability',params={'doctor':'Dr QA','day':'2030-01-12'}).json()
    assert avail['booked_times']==['10:00']
    moved=client.patch(f"/api/reschedule/{a.json()['id']}",json={'day':'2030-01-12','time':'11:00'})
    assert moved.status_code==200 and moved.json()['time']=='11:00'
    assert client.post('/api/items',json={**body,'day':'not-a-date'}).status_code==422



def test_v05_booking_audit():
    a=client.post('/api/items',json={'patient':'Test Person','doctor':'Dr Example','day':'2027-03-04','time':'11:00'}).json()
    assert client.patch(f"/api/reschedule/{a['id']}",json={'day':'2027-03-05','time':'12:00'}).status_code==200
    assert client.patch(f"/api/items/{a['id']}").status_code==200
    history=client.get(f"/api/appointments/{a['id']}/history").json()
    assert [row['action'] for row in history]==['rescheduled','cancelled']

def test_v05_authentication():
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/items').status_code==401
        assert anonymous.post('/api/auth/register',json={'username':'intruder','password':'DemoPassword123!','setup_token':'bad'}).status_code==403

# v0.6 request-origin and owner audit regression
def test_v06_audit_record_and_cross_site_guard():
    attempted=client.post('/api/__audit_probe_404')
    assert attempted.status_code==404
    audit=client.get('/api/auth/audit')
    assert audit.status_code==200
    assert any(row['method']=='POST' and row['path']=='/api/__audit_probe_404'
               and row['status_code']==404 for row in audit.json())
    assert client.get('/api/auth/audit',params={'limit':201}).status_code==422
    blocked=client.post('/api/__audit_probe_404',headers={'sec-fetch-site':'cross-site'})
    assert blocked.status_code==403

def test_canonical_times_prevent_duplicate_slots():
    payload={'patient':'Demo A','doctor':'Dr Time','day':'2031-02-03','time':'10:00'}
    assert client.post('/api/items',json=payload).status_code==201
    assert client.post('/api/items',json={**payload,'time':'10:00:00'}).status_code==422
    assert client.post('/api/items',json={**payload,'time':'10:00+00:00'}).status_code==422
    assert client.post('/api/items',json={**payload,'day':'2031-2-3'}).status_code==422
    assert client.post('/api/items',json={**payload,'day':'2031-02-30'}).status_code==422
    assert client.post('/api/items',json=payload).status_code==409
