from confluent_kafka import Consumer
import json
import time
import sqlite3
from shapely.geometry import Point, Polygon

# Configuração do banco de dados
def setup_database():
    conn = sqlite3.connect('location_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            latitude REAL,
            longitude REAL,
            timestamp REAL,
            accuracy REAL,
            altitude REAL,
            speed REAL,
            battery_level REAL,
            inside_geofence INTEGER
        )
    ''')
    conn.commit()
    return conn

# Configuração do consumidor Kafka
def setup_consumer():
    return Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'location-tracker-server',
        'auto.offset.reset': 'latest'
    })

# Criar alguns geofences de exemplo
def setup_geofences():
    home_geofence = Polygon([
        (-46.6580, -23.5640), (-46.6570, -23.5640),
        (-46.6570, -23.5630), (-46.6580, -23.5630)
    ])
    office_geofence = Polygon([
        (-46.6520, -23.5580), (-46.6510, -23.5580),
        (-46.6510, -23.5570), (-46.6520, -23.5570)
    ])
    return {
        'home': home_geofence,
        'office': office_geofence
    }

# Verificar se um ponto está em algum dos geofences
def check_geofences(lat, lng, geofences):
    point = Point(lng, lat)
    results = {}
    for name, geofence in geofences.items():
        results[name] = geofence.contains(point)
    return results

# Verificar transições de entrada/saída de geofence
def check_geofence_transitions(device_id, current_status, conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT inside_geofence
        FROM locations
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (device_id,))
    
    previous = cursor.fetchone()
    if previous is not None:
        previous_inside = previous[0]
        current_inside = 1 if any(current_status.values()) else 0
        if previous_inside != current_inside:
            if current_inside:
                print(f"[ALERTA] Dispositivo {device_id} **entrou** em uma área monitorada.")
            else:
                print(f"[ALERTA] Dispositivo {device_id} **saiu** da área monitorada.")

# Histórico de localização
def get_location_history(device_id, start_time, end_time):
    conn = sqlite3.connect('location_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT latitude, longitude, timestamp
        FROM locations
        WHERE device_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    ''', (device_id, start_time, end_time))
    return cursor.fetchall()

def main():
    db_conn = setup_database()
    consumer = setup_consumer()
    geofences = setup_geofences()
    consumer.subscribe(['device_locations'])
    
    print("Iniciando servidor de rastreamento...")
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Erro: {msg.error()}")
                continue
            
            try:
                data = json.loads(msg.value().decode('utf-8'))
                device_id = data['device_id']
                lat = data['latitude']
                lng = data['longitude']
                
                geofence_results = check_geofences(lat, lng, geofences)
                inside_any = any(geofence_results.values())

                # Verificar transição de geofence
                check_geofence_transitions(device_id, geofence_results, db_conn)

                # Registrar no banco de dados
                cursor = db_conn.cursor()
                cursor.execute('''
                    INSERT INTO locations 
                    (device_id, latitude, longitude, timestamp, accuracy, 
                     altitude, speed, battery_level, inside_geofence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    device_id, lat, lng, data['timestamp'], data['accuracy'],
                    data['altitude'], data['speed'], data['battery_level'], 
                    1 if inside_any else 0
                ))
                db_conn.commit()

                # Exibir a informação
                print(f"Localização recebida - Dispositivo: {device_id}")
                print(f"Coordenadas: {lat}, {lng}")
                print(f"Dentro de algum geofence: {inside_any}")
                if inside_any:
                    in_fences = [name for name, inside in geofence_results.items() if inside]
                    print(f"Geofences ativos: {', '.join(in_fences)}")
                print("---")

            except Exception as e:
                print(f"Erro ao processar mensagem: {e}")
    
    except KeyboardInterrupt:
        print("Servidor de rastreamento encerrado.")
    finally:
        consumer.close()
        db_conn.close()

if __name__ == "__main__":
    main()
