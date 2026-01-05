from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, username: str, room: str):
        self.active_connections[websocket] = {"username": username, "room": room}
        await self.broadcast_system(room, f"System: {username} joined the room")

    async def disconnect(self, websocket: WebSocket):
        info = self.active_connections.pop(websocket, None)
        if info:
            await self.broadcast_system(info["room"], f"System: {info['username']} left")

    async def broadcast_room(self, room: str, data: dict, sender: WebSocket):
        for ws, info in self.active_connections.items():
            if info["room"] == room and ws != sender:
                await ws.send_json(data)

    async def broadcast_system(self, room: str, message: str):
        for ws, info in self.active_connections.items():
            if info["room"] == room:
                await ws.send_json({"type": "system", "message": message})

manager = ConnectionManager()

@app.get("/")
async def get():
    # This reads your index.html file and sends it to the browser
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        initial_data = await websocket.receive_json()
        username = initial_data.get("username", "Anonymous")
        room = initial_data.get("room", "general")
        
        await manager.connect(websocket, username, room)

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "chat":
                await manager.broadcast_room(room, {
                    "type": "chat",
                    "username": username,
                    "message": data.get("message")
                }, websocket)

            elif event_type in ["typing", "stop_typing"]:
                await manager.broadcast_room(room, {
                    "type": event_type,
                    "username": username
                }, websocket)

    except WebSocketDisconnect:
        await manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)