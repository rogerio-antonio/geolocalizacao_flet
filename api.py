from fastapi import FastAPI, Query, Header, HTTPException
from typing import List, Optional
import sqlite3
from pydantic import BaseModel

from shapely.geometry import Point, Polygon

app = FastAPI()

DATABASE = 'location_tracker.db'
API_KEY = "minha-chave-secreta"

# Geofences
GEOFENCES = {
    'home': Polygon([
        (-46.6580, -23.5640), (-46.6570, -23.5640),
        (-46.6570, -23.5630), (-46.6580, -23.5630)
    ]),
    'office': Polygon([
        (-46.6520, -23.5580), (-46.6510, -23.5580),
        (-46.6510, -23.5570), (-46.6520, -23.5570)
    ])
}

class Location(BaseModel):
    latitude: float
    longitude: float
    timestamp: float

class GeofenceEvent(BaseModel):
    timestamp: float
    entered: Optional[bool]  # True = entrou, False = saiu

def get_connection():
    return sqlite3.connect(DATABASE)

def check_api_key(api_key: Optional[str]):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Chave de API inválida")

def point_in_geofence(lat, lng, geofence_name):
    point = Point(lng, lat)
    return GEOFENCES.get(geofence_name, Polygon()).contains(point)

@app.get("/")
def root():
    return {"message": "API de Rastreamento GPS"}

@app.get("/history", response_model=List[Location])
def get_location_history(
    device_id: str,
    start_time: float,
    end_time: float,
    geofence: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
):
    check_api_key(x_api_key)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT latitude, longitude, timestamp
        FROM locations
        WHERE device_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    ''', (device_id, start_time, end_time))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for lat, lng, ts in rows:
        if geofence:
            if not point_in_geofence(lat, lng, geofence):
                continue
        result.append({"latitude": lat, "longitude": lng, "timestamp": ts})
    return result

@app.get("/last_location", response_model=Location)
def get_last_location(device_id: str, x_api_key: Optional[str] = Header(None)):
    check_api_key(x_api_key)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT latitude, longitude, timestamp
        FROM locations
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (device_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"latitude": row[0], "longitude": row[1], "timestamp": row[2]}
    raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

@app.get("/geofence_events", response_model=List[GeofenceEvent])
def get_geofence_events(
    device_id: str,
    geofence: str,
    start_time: float,
    end_time: float,
    x_api_key: Optional[str] = Header(None)
):
    check_api_key(x_api_key)
    if geofence not in GEOFENCES:
        raise HTTPException(status_code=404, detail="Geofence não encontrado")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT latitude, longitude, timestamp
        FROM locations
        WHERE device_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    ''', (device_id, start_time, end_time))
    rows = cursor.fetchall()
    conn.close()

    last_inside = None
    events = []
    for lat, lng, ts in rows:
        inside = point_in_geofence(lat, lng, geofence)
        if last_inside is None:
            last_inside = inside
            continue
        if inside != last_inside:
            events.append({
                "timestamp": ts,
                "entered": inside
            })
            last_inside = inside
    return events
