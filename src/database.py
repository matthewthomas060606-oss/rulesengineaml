import sqlite3
from pathlib import Path
def createdatabase(detailslist):
    db_dir = Path(__file__).parent.parent / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "sanctions.db"
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor = connection.cursor()
    cursor.execute("PRAGMA user_version")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sanctionslist (
                ssid  TEXT PRIMARY KEY,
                issid  TEXT,
                name  TEXT
            )
        """)
        cursor.execute("PRAGMA user_version = 1")
        connection.commit()
    cursor.executemany("""
        INSERT INTO sanctionslist (ssid, issid, name)
        VALUES (?, ?, ?)
        ON CONFLICT(ssid) DO UPDATE
           SET name = excluded.name
           WHERE sanctionslist.name IS DISTINCT FROM excluded.name
    """, detailslist)
    connection.commit()


def returnDetails2():
    db_path = Path(__file__).parent.parent / "data" / "sanctions.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ssid, issid, name FROM sanctionslist")
    details = cursor.fetchall()
    conn.close()
    return details
