import flet as ft
import sqlite3
import folium
from folium.plugins import HeatMap
import tempfile
import os
import time

def get_last_locations(limit=100):
    conn = sqlite3.connect('location_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT device_id, latitude, longitude, timestamp, inside_geofence
        FROM locations
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    return cursor.fetchall()

def main(page: ft.Page):
    page.title = "Monitoramento de Localização"
    page.theme_mode = ft.ThemeMode.DARK
    
    # Componente para visualizar o mapa
    map_view = ft.WebView(
        width=page.width,
        height=page.height * 0.75,
    )
    
    # Informações do dispositivo
    device_info = ft.Text("Carregando informações do dispositivo...")
    
    # Atualizar o mapa com as localizações mais recentes
    def update_map():
        locations = get_last_locations(100)
        
        if not locations:
            device_info.value = "Nenhuma localização encontrada."
            page.update()
            return
        
        # Criar um mapa temporário com Folium
        m = folium.Map(location=[locations[0][1], locations[0][2]], zoom_start=14)
        
        # Adicionar marcadores para cada localização
        for device_id, lat, lng, timestamp, in_geofence in locations:
            # Converter timestamp para data legível
            date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            
            # Cor do marcador: verde se estiver dentro de um geofence, vermelho caso contrário
            color = 'green' if in_geofence else 'red'
            
            # Adicionar marcador
            folium.Marker(
                [lat, lng], 
                popup=f"Device: {device_id}<br>Time: {date_time}",
                icon=folium.Icon(color=color)
            ).add_to(m)
        
        # Adicionar caminho da trajetória
        path_points = [(lat, lng) for _, lat, lng, _, _ in locations]
        folium.PolyLine(path_points, color="blue", weight=2.5, opacity=0.7).add_to(m)
        
        # Adicionar mapa de calor
        HeatMap(path_points).add_to(m)
        
        # Salvar o mapa em um arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        m.save(temp_file.name)
        
        # Atualizar o WebView com o mapa
        map_view.url = f"file://{temp_file.name}"
        
        # Atualizar informações do dispositivo
        latest = locations[0]
        device_info.value = (
            f"Dispositivo: {latest[0]}\n"
            f"Última localização: {latest[1]:.6f}, {latest[2]:.6f}\n"
            f"Hora: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest[3]))}\n"
            f"Status: {'Dentro de uma área monitorada' if latest[4] else 'Fora das áreas monitoradas'}"
        )
        
        page.update()
    
    # Botão para atualizar o mapa
    refresh_button = ft.ElevatedButton(
        "Atualizar Mapa", 
        icon=ft.icons.REFRESH,
        on_click=lambda _: update_map()
    )
    
    # Layout da página
    page.add(
        ft.AppBar(title=ft.Text("Monitor de Localização"), center_title=True),
        map_view,
        ft.Container(
            content=ft.Column([
                device_info,
                refresh_button,
            ]),
            padding=20
        )
    )
    
    # Atualizar o mapa inicialmente
    update_map()
    
    # Configurar atualizações automáticas
    def auto_refresh():
        update_map()
        page.after(30, auto_refresh)  # Atualizar a cada 30 segundos
    
    page.after(30, auto_refresh)

ft.app(target=main)
