import sqlite3


def create_database():

    conn = sqlite3.connect("monitoring.db")

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT

        )
    """)

    conn.commit()

    conn.close()

    print("Base de données initialisée.")