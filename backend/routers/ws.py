from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps analysis_id to an active WebSocket connection safely
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket Client [{client_id}] connected.")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket Client [{client_id}] DISCONNECTED.")

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                # Transmit pure physical JSON payload
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to transmit WS dict to {client_id}: {e}")
                
    async def broadcast(self, message: str):
        """Standard mass mapping"""
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

router = APIRouter(prefix="/ws", tags=["WebSockets"])

@router.websocket("/analysis/{analysis_id}")
async def websocket_endpoint(websocket: WebSocket, analysis_id: str):
    await manager.connect(websocket, analysis_id)
    try:
        while True:
            # Structurally maintains open pipe expecting pingbacks or idle closure
            data = await websocket.receive_text()
            # We don't necessarily do anything with incoming socket texts 
            # (UI is mainly a receiver listening for python execution streams)
    except WebSocketDisconnect:
        manager.disconnect(analysis_id)
