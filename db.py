import sqlite3
from typing import Callable

DB_NAME = 'data.db'

def create_db_connection(db_name: str) -> tuple[sqlite3.Cursor, sqlite3.Connection]:
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elapsedtime REAL,
            velocity REAL,
            density REAL,
            viscosity REAL,
            tds REAL,
            mass REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return cur, conn

def save_group(readings: list, get_connection: Callable[[str], tuple[sqlite3.Cursor, sqlite3.Connection]], COLUMN_SIZE: int = 6) -> None:
    """
    Open a new database connection, save one group of readings, and then close the connection.
    """
    if len(readings) != COLUMN_SIZE:
        print("Data reading size does not match available database columns.")
        return

    try:
        input_data = [float(reading) for reading in readings]
    except ValueError:
        input_data = readings

    # Open a new connection for this group
    cursor, conn = get_connection(DB_NAME)
    cursor.execute(
        "INSERT INTO readings (elapsedtime, velocity, density, viscosity, tds, mass) VALUES (?, ?, ?, ?, ?, ?)",
        input_data
    )
    conn.commit()
    conn.close()

def view_all_readings(get_connection: Callable[[str], tuple[sqlite3.Cursor, sqlite3.Connection]]) -> list:
    """
    Open a connection, fetch all rows from the readings table, and close the connection.
    """
    cursor, conn = get_connection(DB_NAME)
    cursor.execute('SELECT * FROM readings ORDER BY id DESC')
    records = cursor.fetchall()
    conn.close()
    return records

def view_latest_readings(get_connection: Callable[[str], tuple[sqlite3.Cursor, sqlite3.Connection]], limit: int = 10) -> list:
    """
    Open a connection, fetch the latest records from the readings table, and close the connection.
    """
    cursor, conn = get_connection(DB_NAME)
    cursor.execute('SELECT * FROM readings ORDER BY id DESC LIMIT ?', (limit,))
    records = cursor.fetchall()
    conn.close()
    
    return records

def view_latest_readings_before_id(get_connection: Callable[[str], tuple[sqlite3.Cursor, sqlite3.Connection]], id: int, limit: int = 5) -> list:
    """
    Open a connection, fetch the 5 readings before the given id from the readings table, and close the connection.
    """
    cursor, conn = get_connection(DB_NAME)
    cursor.execute('SELECT * FROM readings WHERE id < ? ORDER BY id DESC LIMIT ?', (id, limit))
    records = cursor.fetchall()
    conn.close()
    return records