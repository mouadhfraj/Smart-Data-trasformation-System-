# smart_system/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist


logger = logging.getLogger(__name__)


class ExecutionConsumer(AsyncWebsocketConsumer):
    """Enhanced WebSocket consumer with better connection handling"""

    async def connect(self):
        """Handle connection with proper validation"""
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f'execution_{self.execution_id}'





        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"WebSocket connected for execution {self.execution_id}")



    async def disconnect(self, close_code):
        """Handle disconnection with proper cleanup"""
        logger.info(f"WebSocket disconnecting for execution {self.execution_id}, code: {close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages with proper error handling"""
        try:
            data = json.loads(text_data)

            # Handle heartbeat pings
            if data.get('type') == 'heartbeat':
                await self.send(text_data=json.dumps({'type': 'heartbeat', 'message': 'pong'}))
                return

            # Process other message types...

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    async def execution_update(self, event):
        """Send updates to client with error handling"""
        try:
            await self.send(text_data=json.dumps({
                'message': event['message'],
                'timestamp': event.get('timestamp')
            }))
        except Exception as e:
            logger.error(f"Error sending update: {str(e)}")
            await self.close(code=1011)