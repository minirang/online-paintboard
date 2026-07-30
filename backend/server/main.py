import os
import json
import sqlite3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

if not os.path.exists("../db"):
    os.makedirs("../db")

conn = sqlite3.connect("../db/paintboard.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS draw_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lastX REAL,
    lastY REAL,
    currentX REAL,
    currentY REAL,
    color TEXT,
    size INTEGER
)
""")
conn.commit()

active_connections = []
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome"}

@app.delete("/api/clear")
def clear_canvas():
    try:
        cursor.execute("DELETE FROM draw_history")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='draw_history'")
        conn.commit()
        return {"status": "success", "message": "Canvas history cleared successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    cursor.execute(
        "SELECT lastX, lastY, currentX, currentY, color, size FROM draw_history ORDER BY id ASC"
    )
    rows = cursor.fetchall()
    for row in rows:
        history_data = {
            "type": "HISTORY",
            "lastX": row[0],
            "lastY": row[1],
            "currentX": row[2],
            "currentY": row[3],
            "color": row[4],
            "size": row[5],
        }
        await websocket.send_text(json.dumps(history_data))
    active_connections.append(websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)

            cursor.execute(
                """
                INSERT INTO draw_history (lastX, lastY, currentX, currentY, color, size)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    data["lastX"],
                    data["lastY"],
                    data["currentX"],
                    data["currentY"],
                    data["color"],
                    data["size"],
                ),
            )
            conn.commit()

            for connection in active_connections:
                if connection != websocket:
                    await connection.send_text(raw_data)

    except WebSocketDisconnect:
        active_connections.remove(websocket)
