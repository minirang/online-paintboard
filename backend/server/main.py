from __future__ import annotations
import os
import json
import secrets
import asyncio
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

env_path = Path(__file__).parent / ".env"
print("Loading env:", env_path)
load_dotenv(dotenv_path=env_path)
DB_URL = os.getenv("DATABASE_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
conn = psycopg2.connect(DB_URL)
print("Connected to the database.")

token_store: set[str] = set()
db_queue: asyncio.Queue | None = None
active_connections: list[WebSocket] = []


class ClearRequest(BaseModel):
    password: str


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    global db_queue
    db_queue = asyncio.Queue()
    asyncio.create_task(db_consumer())


async def db_consumer():
    while True:
        req = await db_queue.get()
        try:
            if req["type"] == "history":
                result = _fetch_history()
                req["future"].set_result(result)
            elif req["type"] == "insert":
                _db_insert(req["data"])
            elif req["type"] == "clear":
                _clear_canvas()
                req["future"].set_result(None)
        except Exception as e:
            future = req.get("future")
            if future is not None and not future.done():
                future.set_exception(e)
            else:
                print("DB error:", e)
        db_queue.task_done()


def _fetch_history():
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT lastX, lastY, currentX, currentY, color, size
            FROM draw_history
            ORDER BY id ASC
        """)
        return cursor.fetchall()
    finally:
        cursor.close()


def _db_insert(data):
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO draw_history
            (lastX, lastY, currentX, currentY, color, size)
            VALUES (%s, %s, %s, %s, %s, %s)
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
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def _clear_canvas():
    cursor = conn.cursor()
    try:
        cursor.execute("TRUNCATE TABLE draw_history RESTART IDENTITY;")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


async def _db_request(req_type, data=None):
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    await db_queue.put({"type": req_type, "data": data, "future": future})
    return await future


@app.get("/")
def read_root():
    return {"message": "Welcome"}


@app.get("/api/ws-token")
def issue_token():
    token = secrets.token_urlsafe(32)
    token_store.add(token)
    return {"token": token}


@app.post("/api/clear")
async def clear_canvas(payload: ClearRequest):
    if not ADMIN_PASSWORD or payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    try:
        await _db_request("clear")
        clear_message = json.dumps({"type": "CLEAR"})
        for connection in active_connections[:]:
            try:
                await connection.send_text(clear_message)
            except Exception:
                if connection in active_connections:
                    active_connections.remove(connection)
        return {"status": "success", "message": "Canvas history cleared successfully"}
    except Exception:
        raise HTTPException(status_code=500, detail="Database operation failed")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token or token not in token_store:
        await websocket.accept()
        await websocket.close(code=1008)
        return
    token_store.discard(token)

    await websocket.accept()
    try:
        rows = await _db_request("history")
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

            db_queue.put_nowait({"type": "insert", "data": data})

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

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

    except Exception as e:
        print("WebSocket error:", e)
        if websocket in active_connections:
            active_connections.remove(websocket)
