from fastapi import WebSocket
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps channel name (e.g. "{trip_id}:status" or "{trip_id}:votes") to a set of connected WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        logger.info(f"WebSocket client connected to channel '{channel}'. Active connections: {len(self.active_connections[channel])}")

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            logger.info(f"WebSocket client disconnected from channel '{channel}'. Remaining: {len(self.active_connections[channel])}")
            if not self.active_connections[channel]:
                del self.active_connections[channel]

    async def broadcast(self, message: dict, channel: str):
        if channel in self.active_connections:
            # Create a copy to prevent RuntimeError during concurrent modifications
            connections = list(self.active_connections[channel])
            logger.debug(f"Broadcasting to {len(connections)} clients on channel '{channel}'")
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Error sending message to client on channel '{channel}': {e}. Removing connection.")
                    self.active_connections[channel].discard(connection)

manager = ConnectionManager()
