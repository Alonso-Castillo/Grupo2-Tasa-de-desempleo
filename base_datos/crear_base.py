
from pathlib import Path
import sqlite3

# 1. Definir la ubicación de nuestra base de datos
RUTA_DB = Path(__file__).resolve().parent / "desempleo_chile.db"

# 2. Conectarnos a SQLite
with sqlite3.connect(RUTA_DB) as conexion:

    # Activar las relaciones entre tablas
    conexion.execute("PRAGMA foreign_keys = ON")

    # 3. Crear las tres tablas
    conexion.executescript("""
    
    CREATE TABLE IF NOT EXISTS temas (
        id_tema INTEGER PRIMARY KEY,
        tema TEXT NOT NULL UNIQUE,
        descripcion TEXT
    );

    CREATE TABLE IF NOT EXISTS series (
        id_serie TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        fuente TEXT NOT NULL,
        frecuencia TEXT NOT NULL,
        unidad TEXT,
        id_tema INTEGER NOT NULL,
        FOREIGN KEY (id_tema) REFERENCES temas(id_tema)
    );

    CREATE TABLE IF NOT EXISTS observaciones (
        id_serie TEXT NOT NULL,
        fecha TEXT NOT NULL,
        valor REAL,
        PRIMARY KEY (id_serie, fecha),
        FOREIGN KEY (id_serie) REFERENCES series(id_serie)
    );
    
    """)

    # 4. Verificar las tablas creadas
    tablas = conexion.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

print("Base de datos creada correctamente")
print("Ubicación:", RUTA_DB)
print("Tablas creadas:", [tabla[0] for tabla in tablas])
