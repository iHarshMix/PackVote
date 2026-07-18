from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from packvote.backend.websockets.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])

@router.websocket("/ws/{trip_id}/{channel_type}")
async def websocket_endpoint(websocket: WebSocket, trip_id: str, channel_type: str):
    channel = f"{trip_id}:{channel_type}"
    await manager.connect(websocket, channel)
    logger.info(f"WebSocket client connected to channel: {channel}")
    try:
        while True:
            # Keep the connection open and receive message if client sends any
            # (e.g. for pings or keeping the connection alive)
            data = await websocket.receive_text()
            logger.debug(f"Received data from client on channel '{channel}': {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
        logger.info(f"WebSocket client disconnected cleanly from channel: {channel}")
    except Exception as e:
        logger.error(f"WebSocket exception on channel '{channel}': {e}", exc_info=True)
        manager.disconnect(websocket, channel)
