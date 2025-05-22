from typing import Callable
import serial
import sqlite3

from db import create_db_connection, save_group, view_all_readings

PORT, BAUD_RATE = 'COM3', 9600
GROUP_SIZE, TOTAL_GROUPS = 6, 3
TIMEOUT = 1

def open_serial_connection(port: str, baud_rate: int, timeout: float) -> serial.Serial:
    ser = serial.Serial(port, baud_rate, timeout=timeout)
    if not ser.is_open:
        ser.open()
    print("COM Port open:", ser.is_open)
    return ser

def read_serial_line(ser: serial.Serial) -> float:
    """
    Read one line from the serial port, decode it, strip whitespace and any trailing commas,
    and convert it to a float.
    """
    return float(ser.readline().decode('utf-8').strip().rstrip(','))

def collect_serial_data(ser: serial.Serial, get_connection: Callable[[str], tuple[sqlite3.Cursor, sqlite3.Connection]]) -> None:
    """
    Collect data groups from the serial connection until TOTAL_GROUPS are collected.
    """
    current_group = []

    while True:
        if ser.in_waiting:
            data_entry = read_serial_line(ser)
            current_group.append(data_entry)
            if len(current_group) == GROUP_SIZE:
                save_group(current_group, get_connection)
                saved_readings = view_all_readings(create_db_connection)
                print("DB RECORD:", saved_readings[0])
                current_group = []
               
    

def main() -> None:
    try:
        ser = open_serial_connection(PORT, BAUD_RATE, TIMEOUT)
        collect_serial_data(ser, create_db_connection)
    except KeyboardInterrupt:
        print("Shutting app.")
    except Exception as err:
        print("Error", err)
    finally:
        ser.close()

if __name__ == "__main__":
    main()
