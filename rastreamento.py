import flet as ft
import requests
import folium
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"
API_KEY = "minha-chave-secreta"

def build_map(locations):
    fmap = folium.Map(location=[-23.56, -46.65], zoom_start=15)
    for loc in locations:
        folium.CircleMarker(
            location=[loc["latitude"], loc["longitude"]],
            radius=5,
            popup=str(datetime.fromtimestamp(loc["timestamp"])),
            color="blue",
            fill=True,
        ).add_to(fmap)
    fmap.save("map.html")

def main(page: ft.Page):
    page.title = "Painel de Rastreamento"
    page.scroll = "auto"

    device_id = ft.TextField(label="ID do Dispositivo", value="abc123", width=300)
    geofence = ft.TextField(label="Geofence (opcional)", width=300)
    start_date = ft.TextField(label="Início (YYYY-MM-DD)", value=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
    end_date = ft.TextField(label="Fim (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))

    map_view = ft.IFrame(src="map.html", width=700, height=500)
    map_output = ft.Text()

    alert_table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("Timestamp")),
            ft.DataColumn(label=ft.Text("Evento")),
            ft.DataColumn(label=ft.Text("Geofence")),
        ],
        rows=[],
        width=700
    )
    alert_output = ft.Text()

    def consultar_mapa(e):
        try:
            start_ts = datetime.strptime(start_date.value, "%Y-%m-%d").timestamp()
            end_ts = datetime.strptime(end_date.value, "%Y-%m-%d").timestamp()
            params = {
                "device_id": device_id.value,
                "start_time": start_ts,
                "end_time": end_ts
            }
            if geofence.value:
                params["geofence"] = geofence.value

            r = requests.get(f"{API_URL}/history", params=params, headers={"x-api-key": API_KEY})
            r.raise_for_status()
            data = r.json()
            map_output.value = f"{len(data)} pontos encontrados."
            if data:
                build_map(data)
                map_view.src = "map.html"
                page.update()
        except Exception as err:
            map_output.value = f"Erro: {err}"
            page.update()

    def consultar_alertas(e):
        try:
            start_ts = datetime.strptime(start_date.value, "%Y-%m-%d").timestamp()
            end_ts = datetime.strptime(end_date.value, "%Y-%m-%d").timestamp()
            params = {
                "device_id": device_id.value,
                "start_time": start_ts,
                "end_time": end_ts
            }

            r = requests.get(f"{API_URL}/alerts", params=params, headers={"x-api-key": API_KEY})
            r.raise_for_status()
            data = r.json()
            alert_output.value = f"{len(data)} alertas encontrados."
            alert_table.rows = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(datetime.fromtimestamp(a["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"))),
                    ft.DataCell(ft.Text(a["event"])),
                    ft.DataCell(ft.Text(a["geofence"]))
                ]) for a in data
            ]
            page.update()
        except Exception as err:
            alert_output.value = f"Erro: {err}"
            page.update()

    mapa_tab = ft.Column([
        ft.Row([device_id, geofence]),
        ft.Row([start_date, end_date]),
        ft.ElevatedButton("Consultar Histórico", on_click=consultar_mapa),
        map_output,
        map_view
    ])

    alertas_tab = ft.Column([
        ft.Row([device_id]),
        ft.Row([start_date, end_date]),
        ft.ElevatedButton("Consultar Alertas", on_click=consultar_alertas),
        alert_output,
        alert_table
    ])

    page.add(
        ft.Tabs(tabs=[
            ft.Tab(text="📍 Mapa", content=mapa_tab),
            ft.Tab(text="⚠️ Alertas", content=alertas_tab),
        ])
    )

ft.app(target=main)
