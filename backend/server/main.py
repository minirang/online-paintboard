import os
import json
import secrets
import hmac
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2 import pool as psycopg2_pool

env_path = Path(__file__).parent / ".env"
print("Loading env:", env_path)
load_dotenv(dotenv_path=env_path)

DB_URL = os.getenv("DATABASE_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

db_pool = psycopg2_pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=10,
    dsn=DB_URL,
)
print("Database connection pool created.")

active_connections: list[WebSocket] = []
active_tokens: set[str] = set()
pending_strokes: list[dict] = []
strokes_lock = asyncio.Lock()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome"}


@app.get("/api/token")
def issue_token():
    token = secrets.token_urlsafe(32)
    active_tokens.add(token)
    return {"token": token}


@app.post("/api/clear")
async def clear_canvas(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid request"},
        )

    password = body.get("password", "")
    if not ADMIN_PASSWORD or not hmac.compare_digest(password, ADMIN_PASSWORD):
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Not authorized"},
        )

    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("TRUNCATE TABLE draw_history RESTART IDENTITY;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Database error during clear:", e)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Database operation failed"},
        )
    finally:
        cursor.close()
        db_pool.putconn(conn)

    clear_msg = json.dumps({"type": "CLEAR"})
    for connection in active_connections[:]:
        try:
            await connection.send_text(clear_msg)
        except Exception:
            if connection in active_connections:
                active_connections.remove(connection)
            try:
                await connection.close()
            except Exception:
                pass

    return {"status": "success", "message": "Canvas history cleared successfully"}


async def flush_strokes() -> None:
    async with strokes_lock:
        if not pending_strokes:
            return
        strokes_to_write = pending_strokes[:]
        pending_strokes.clear()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _batch_insert, strokes_to_write)


def _batch_insert(strokes: list[dict]) -> None:
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        values = []
        for s in strokes:
            values.append(
                (
                    s["lastX"],
                    s["lastY"],
                    s["currentX"],
                    s["currentY"],
                    s["color"],
                    s["size"],
                )
            )
        args = b",".join(
            cursor.mogrify("(%s,%s,%s,%s,%s,%s)", v) for v in values
        ).decode()
        cursor.execute(f"""
            INSERT INTO draw_history
            (lastX, lastY, currentX, currentY, color, size)
            VALUES {args}
            """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Batch insert error:", e)
    finally:
        cursor.close()
        db_pool.putconn(conn)


async def stroke_writer_task() -> None:
    while True:
        await asyncio.sleep(0.5)
        await flush_strokes()


@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(stroke_writer_task())


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    if not token or token not in active_tokens:
        await websocket.close(code=4001, reason="Invalid token")
        return

    active_tokens.discard(token)
    await websocket.accept()
    loop = asyncio.get_event_loop()

    def _fetch_history() -> list[tuple]:
        conn = db_pool.getconn()
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
            db_pool.putconn(conn)

    rows = await loop.run_in_executor(None, _fetch_history)

    history_payload = {
        "type": "HISTORY",
        "strokes": [
            {
                "lastX": row[0],
                "lastY": row[1],
                "currentX": row[2],
                "currentY": row[3],
                "color": row[4],
                "size": row[5],
            }
            for row in rows
        ],
    }
    await websocket.send_text(json.dumps(history_payload))

    active_connections.append(websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if not (1 <= int(data["size"]) <= 20):
                continue

            async with strokes_lock:
                pending_strokes.append(data)

            for connection in active_connections[:]:
                if connection == websocket:
                    continue
                try:
                    await connection.send_text(raw_data)
                except Exception:
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
