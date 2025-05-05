# smart_system/websocket_utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def send_execution_update(execution_id, data):
    """
    Enhanced WebSocket update sender with better error handling

    Args:
        execution_id: The execution ID to send updates to
        data: Dictionary containing:
            - status: RUNNING|COMPLETED|FAILED
            - logs: String log content
            - build_url: Optional build URL
            - build_number: Optional build number
            - error: Optional error message
    """
    try:
        # Standardize message format
        message = {
            'status': data.get('status', 'RUNNING').upper(),
            'logs': data.get('logs', ''),
            'timestamp': data.get('timestamp', datetime.now().isoformat()),

        }

        # Add optional fields
        if 'build_url' in data:
            message['build_url'] = data['build_url']
        if 'build_number' in data:
            message['build_number'] = data['build_number']
        if 'error' in data:
            message['error'] = data['error']
        if 'end_time' in data:
            message['end_time'] = data['end_time']

        logger.info(f"Sending update for execution {execution_id}: {message['status']}")

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'execution_{execution_id}',
            {
                'type': 'execution_update',
                'message': message
            }
        )
    except Exception as e:
        logger.error(f"Failed to send WebSocket update: {str(e)}")
        raise