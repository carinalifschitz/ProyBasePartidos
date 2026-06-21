import requests
import sqlite3
from datetime import datetime, timedelta
import time

# Configuración de cabeceras para evitar bloqueos
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def conectar_db():
    # Usamos SQLite local para el ejemplo, cámbialo por psycopg2 si usas PostgreSQL
    return sqlite3.connect('trivia_futbol_completa.db')

def obtener_partidos_dia_anterior():
    """Busca la lista de IDs de partidos jugados ayer"""
    ayer = datetime.now() - timedelta(days=1)
    fecha_str = ayer.strftime("%Y%m%d") # Formato: 20260620
    
    # Endpoint del calendario de torneos de FIFA/Internacionales
    url_agenda = f"https://espn.com{fecha_str}"
    
    try:
        respuesta = requests.get(url_agenda, headers=HEADERS, timeout=15)
        if respuesta.status_code != 200:
            return []
        
        datos = respuesta.json()
        ids_partidos = []
        for evento in datos.get('events', []):
            ids_partidos.append(evento.get('id'))
        return ids_partidos
    except Exception as e:
        print(f"Error al obtener agenda del día anterior: {e}")
        return []

def procesar_y_guardar_detalle(id_partido):
    """Extrae el resumen, estadísticas, jugadores y goles de un partido específico"""
    url_detalle = f"https://espn.com{id_partido}"
    
    try:
        respuesta = requests.get(url_detalle, headers=HEADERS, timeout=15)
        if respuesta.status_code != 200:
            return
        
        datos = respuesta.json()
        header = datos.get('header', {})
        competitions = header.get('competitions', [{}])[0]
        competitors = competitions.get('competitors', [])
        
        if len(competitors) < 2:
            return

        # 1. Clasificar Local y Visitante
        local = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
        visitante = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
        
        # Datos generales del partido
        liga = header.get('league', {}).get('name', 'Internacional')
        fecha_partido = header.get('date')
        
        eq_local_id = local.get('team', {}).get('id')
        eq_local_nom = local.get('team', {}).get('name')
        goles_local = int(local.get('score', 0))
        
        eq_vis_id = visitante.get('team', {}).get('id')
        eq_vis_nom = visitante.get('team', {}).get('name')
        goles_vis = int(visitante.get('score', 0))
        
        ganador = 'empate'
        if goles_local > goles_vis: ganador = 'local'
        elif goles_vis > goles_local: ganador = 'visitante'
        
        # Verificar si hubo tanda de penales en el nodo de shootouts
        hubo_penales = False
        pen_local, pen_vis = 0, 0
        if 'shootout' in competitions:
            hubo_penales = True
            # Lógica para contar los penales anotados si están disponibles en el JSON
            
        # --- Guardar Partido General ---
        conn = conectar_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO partidos 
            (id_partido, fecha_partido, liga_nombre, equipo_local_id, equipo_local_nombre, equipo_local_goles, equipo_visitante_id, equipo_visitante_nombre, equipo_visitante_goles, ganador, tanda_penales, penales_local, penales_visitante)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id_partido, fecha_partido, liga, eq_local_id, eq_local_nom, goles_local, eq_vis_id, eq_vis_nom, goles_vis, ganador, hubo_penales, pen_local, pen_vis))

        # 2. Extraer Jugadores (Rosters / Lineups)
        # Nota: Dependiendo del torneo, ESPN guarda las alineaciones en el nodo 'rosters' o 'lineups'
        for equipo_roster in datos.get('rosters', []):
            id_equipo = equipo_roster.get('team', {}).get('id')
            for jugador_entry in equipo_roster.get('roster', []):
                id_jugador = jugador_entry.get('athlete', {}).get('id')
                nombre_jugador = jugador_entry.get('athlete', {}).get('displayName')
                posicion = jugador_entry.get('athlete', {}).get('position', {}).get('name', 'Desconocido')
                titular = jugador_entry.get('starter', True)
                
                id_registro = f"{id_partido}_{id_jugador}"
                
                cursor.execute('''
                    INSERT OR REPLACE INTO jugadores_partido (id_registro, id_partido, id_equipo, id_jugador, nombre_jugador, posicion, titular)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (id_registro, id_partido, id_equipo, id_jugador, nombre_jugador, posicion, titular))

        # 3. Extraer Incidentes (Goles, Penales anotados/fallados)
        # Los detalles de jugadas y goles suelen venir en el nodo 'keyEvents' o 'details' de la competencia
        for detalle in competitions.get('details', []):
            # Filtrar solo eventos relevantes para preguntas de trivia (Goles/Penales)
            tipo_detalle = detalle.get('type', {}).get('text', '')
            if 'Goal' in tipo_detalle or 'Penalty' in tipo_detalle:
                id_evento = detalle.get('id', f"{id_partido}_{time.time_ns()}")
                id_equipo_evento = detalle.get('team', {}).get('id')
                id_atleta = detalle.get('athletesInvolved', [{}])[0].get('id', '0')
                nom_atleta = detalle.get('athletesInvolved', [{}])[0].get('displayName', 'Desconocido')
                minuto = detalle.get('clock', {}).get('displayValue', '0').replace("'", "")
                periodo = detalle.get('type', {}).get('period', '1H')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO eventos_partido (id_evento, id_partido, id_equipo, id_jugador, nombre_jugador, tipo_evento, minuto, periodo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (id_evento, id_partido, id_equipo_evento, id_atleta, nom_atleta, tipo_detalle, minuto, periodo))

        conn.commit()
        conn.close()
        print(f"-> Procesado con éxito partido ID: {id_partido} ({eq_local_nom} vs {eq_vis_nom})")
        
    except Exception as e:
        print(f"Error procesando el detalle del partido {id_partido}: {e}")

def tarea_diaria_extraccion():
    print(f"[{datetime.now()}] Iniciando descarga de partidos de ayer...")
    partidos_ayer = obtener_partidos_dia_anterior()
    print(f"Se encontraron {len(partidos_ayer)} partidos para procesar.")
    
    for id_p in partidos_ayer:
        procesar_y_guardar_detalle(id_p)
        time.sleep(2) # Pausa de 2 segundos entre partidos para no saturar ni levantar alertas en ESPN
    print(f"[{datetime.now()}] Extracción diaria completada.")

if __name__ == "__main__":
    # Si lo ejecutas manualmente, correrá inmediatamente
    tarea_diaria_extraccion()
