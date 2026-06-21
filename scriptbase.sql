-- 1. Tabla General de Partidos
CREATE TABLE IF NOT EXISTS partidos (
    id_partido VARCHAR(50) PRIMARY KEY,
    fecha_partido TIMESTAMP,
    liga_nombre VARCHAR(100),
    equipo_local_id VARCHAR(50),
    equipo_local_nombre VARCHAR(100),
    equipo_local_goles INT DEFAULT 0,
    equipo_visitante_id VARCHAR(50),
    equipo_visitante_nombre VARCHAR(100),
    equipo_visitante_goles INT DEFAULT 0,
    ganador VARCHAR(20), -- 'local', 'visitante', 'empate'
    tanda_penales BOOLEAN DEFAULT FALSE,
    penales_local INT DEFAULT 0,
    penales_visitante INT DEFAULT 0,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Jugadores por Partido (Alineaciones/Rosters)
CREATE TABLE IF NOT EXISTS jugadores_partido (
    id_registro VARCHAR(100) PRIMARY KEY, -- Combinación id_partido + id_jugador
    id_partido VARCHAR(50),
    id_equipo VARCHAR(50),
    id_jugador VARCHAR(50),
    nombre_jugador VARCHAR(150),
    posicion VARCHAR(50),
    titular BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (id_partido) REFERENCES partidos(id_partido)
);

-- 3. Tabla de Incidentes/Eventos Críticos (Goles, Penales, Tarjetas)
CREATE TABLE IF NOT EXISTS eventos_partido (
    id_evento VARCHAR(50) PRIMARY KEY,
    id_partido VARCHAR(50),
    id_equipo VARCHAR(50),
    id_jugador VARCHAR(50),
    nombre_jugador VARCHAR(150),
    tipo_evento VARCHAR(50), -- 'Gol', 'Autogol', 'Penal Convertido', 'Penal Fallado', 'Tarjeta Roja'
    minuto INT,
    periodo VARCHAR(20), -- '1H', '2H', 'ET1', 'ET2', 'PEN'
    FOREIGN KEY (id_partido) REFERENCES partidos(id_partido)
);
