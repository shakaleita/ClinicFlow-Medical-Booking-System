APP_TITLE = 'ClinicFlow'
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import sqlite3, os
from contextlib import contextmanager
from pathlib import Path

DB = Path(os.environ.get("APP_DB", str(Path(__file__).parent / "app.db")))
app = FastAPI(title=APP_TITLE, version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["*"], allow_headers=["*"])

@contextmanager
def db():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def rows(cursor):
    return [dict(r) for r in cursor.fetchall()]

def setup(sql):
    with db() as con:
        con.executescript(sql)

@app.get("/api/health")
def health():
    return {"ok": True, "service": APP_TITLE}


setup("""CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY,patient TEXT NOT NULL,doctor TEXT NOT NULL,day TEXT NOT NULL,time TEXT NOT NULL,reason TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'Booked');CREATE UNIQUE INDEX IF NOT EXISTS unique_active_slot ON appointments(doctor,day,time) WHERE status='Booked';""")
class Appointment(BaseModel):
    patient:str
    doctor:str
    day:str
    time:str
    reason:str=""
    status:str="Booked"
@app.get('/api/items')
def items():
    with db() as c:return rows(c.execute('SELECT * FROM appointments ORDER BY day DESC,time DESC'))
@app.post('/api/items',status_code=201)
def create_item(a:Appointment):
    if not all([a.patient.strip(),a.doctor.strip(),a.day,a.time]):raise HTTPException(422,'Required appointment fields missing')
    verify_slot(a.day,a.time)
    try:
        with db() as c:
            cur=c.execute('INSERT INTO appointments(patient,doctor,day,time,reason,status) VALUES(?,?,?,?,?,?)',(a.patient,a.doctor,a.day,a.time,a.reason,'Booked'))
            return dict(c.execute('SELECT * FROM appointments WHERE id=?',(cur.lastrowid,)).fetchone())
    except sqlite3.IntegrityError:raise HTTPException(409,'Doctor already booked at this time')
@app.patch('/api/items/{item_id}')
def cancel(item_id:int):
    with db() as c:
        cur=c.execute("UPDATE appointments SET status='Cancelled' WHERE id=? AND status='Booked'",(item_id,))
        if not cur.rowcount:raise HTTPException(404,'Active appointment not found')
        return {'id':item_id,'status':'Cancelled'}
@app.get('/api/summary')
def summary():
    with db() as c:return rows(c.execute('SELECT status AS label, COUNT(*) AS value FROM appointments GROUP BY status'))


# v0.3: appointment availability and rescheduling
from datetime import date as _date
from datetime import time as _time

class Reschedule(BaseModel):
    day: str
    time: str

def verify_slot(day: str, slot: str):
    try:
        _date.fromisoformat(day)
        _time.fromisoformat(slot)
    except ValueError:
        raise HTTPException(422,'Use ISO date YYYY-MM-DD and time HH:MM')

@app.get('/api/availability')
def availability(doctor: str, day: str):
    verify_slot(day,'09:00')
    if not doctor.strip():
        raise HTTPException(422,'Doctor required')
    with db() as con:
        booked = con.execute("SELECT time FROM appointments WHERE doctor=? AND day=? AND status='Booked' ORDER BY time", (doctor,day))
        return {'doctor':doctor,'day':day,'booked_times':[r['time'] for r in booked]}

@app.patch('/api/reschedule/{item_id}')
def reschedule(item_id: int, slot: Reschedule):
    verify_slot(slot.day,slot.time)
    try:
        with db() as con:
            existing=con.execute('SELECT * FROM appointments WHERE id=?',(item_id,)).fetchone()
            if not existing or existing['status']!='Booked':
                raise HTTPException(404,'Active appointment not found')
            con.execute('UPDATE appointments SET day=?,time=? WHERE id=?',(slot.day,slot.time,item_id))
            return dict(con.execute('SELECT * FROM appointments WHERE id=?',(item_id,)).fetchone())
    except sqlite3.IntegrityError:
        raise HTTPException(409,'Doctor already booked at this time')

