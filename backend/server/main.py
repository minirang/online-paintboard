from fastapi import FastAPI, WebSocket, WebSocketDisconnect

active_connections = []
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for connection in active_connections:
                if connection != websocket:
                    await connection.send_text(data)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
