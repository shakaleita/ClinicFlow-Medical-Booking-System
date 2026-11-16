import importlib,os,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temp = tempfile.mkdtemp(prefix='portfolio-test-')
os.environ['APP_DB']=str(Path(temp)/'test.db')
if 'main' in sys.modules: del sys.modules['main']
from main import app
client=TestClient(app)

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

