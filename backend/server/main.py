import os
import json
import uuid
import asyncio
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware

env_path = Path(__file__).parent / ".env"
print("Loading env:", env_path)
load_dotenv(dotenv_path=env_path)
DB_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DB_URL)
print("Connected to the database.")
active_connections = []
pending_tokens = set()
db_queue = asyncio.Queue()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def db_bulk_worker():
    while True:
        await asyncio.sleep(0.5)
        if db_queue.empty():
            continue

        batch = []
        while not db_queue.empty() and len(batch) < 500:
            batch.append(await db_queue.get())
            db_queue.task_done()

        if batch:
            await asyncio.to_thread(_sync_bulk_save, batch)


def _sync_bulk_save(batch):
    cursor = conn.cursor()
    try:
        args_str = ",".join(
            cursor.mogrify(
                "(%s, %s, %s, %s, %s, %s)",
                (
                    d["lastX"],
                    d["lastY"],
                    d["currentX"],
                    d["currentY"],
                    d["color"],
                    d["size"],
                ),
            ).decode("utf-8")
            for d in batch
        )
        cursor.execute(
            f"INSERT INTO draw_history (lastX, lastY, currentX, currentY, color, size) VALUES {args_str}"
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Database error:", e)
    finally:
        cursor.close()


@app.get("/")
def read_root():
    return {"message": "Welcome"}


@app.get("/api/token")
def generate_one_time_token():
    token = str(uuid.uuid4())
    pending_tokens.add(token)
    return {"token": token}


@app.delete("/api/clear")
def clear_canvas():
    cursor = conn.cursor()
    try:
        cursor.execute("TRUNCATE TABLE draw_history RESTART IDENTITY;")
        conn.commit()
        return {"status": "success", "message": "Canvas history cleared successfully"}

    except Exception as e:
        conn.rollback()
        print("Database error:", e)
        return {"status": "error", "message": "Database operation failed"}
    finally:
        cursor.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    if not token or token not in pending_tokens:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    pending_tokens.remove(token)
    await websocket.accept()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT lastX, lastY, currentX, currentY, color, size
            FROM draw_history
            ORDER BY id ASC
        """)

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
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if not (1 <= int(data["size"]) <= 20):
                continue

            for connection in active_connections[:]:
                if connection == websocket:
                    continue
                try:
                    await connection.send_text(raw_data)
                except Exception as e:
                    print("Removing dead websocket:", e)
                    if connection in active_connections:
                        active_connections.remove(connection)
                    try:
                        await connection.close()
                    except Exception:
                        pass

            db_queue.put_nowait(data)

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

    except Exception as e:
        print("WebSocket error:", e)
        if websocket in active_connections:
            active_connections.remove(websocket)

    finally:
        cursor.close()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(db_bulk_worker())
