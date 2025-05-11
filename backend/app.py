import json
import logging
import os
import uuid
from datetime import datetime

from flask import session
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import redis
from rq import Queue
from dotenv import load_dotenv
from llm.chat_agent import ethical_agent
from config.generated_config import SEBASTIAN_CASE

# Cargar configuraciones
load_dotenv()

ORIGIN_DOMAIN = os.getenv("API_BASE_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

CONVERSATION_WINDOW = 50
CHAT_HISTORY_KEY_PREFIX = "chat_history:"

app = Flask(__name__)
app.secret_key = "your_secret_key"
CORS(app, resources={r"/*": {"origins": [f"https://{ORIGIN_DOMAIN}", "http://localhost:3000"]}})
socketio = SocketIO(app, async_mode='eventlet', message_queue=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}", cors_allowed_origins=[f"https://{ORIGIN_DOMAIN}", "http://localhost:3000"])

# Configuración de Redis y la cola
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False, db=REDIS_DB)
task_queue = Queue(connection=redis_client)

def get_timestamp():
    """Generar un timestamp estandarizado."""
    return datetime.utcnow().isoformat() + "Z"  # UTC

def process_message_task(room_id: str):
    """Background task to process messages and generate responses"""
    try:
        # Get recent conversation history
        chat_history_key = f"{CHAT_HISTORY_KEY_PREFIX}{room_id}"
        raw_messages = redis_client.lrange(chat_history_key, -CONVERSATION_WINDOW, -1)
        conversation = [json.loads(msg) for msg in raw_messages]

        # Get agent response
        agent_response = ethical_agent.manage_conversation(
            case=SEBASTIAN_CASE,
            conversation=conversation
        )

        if agent_response["should_intervene"]:
            bot_message = {
                'user_name': 'Bot',
                'message': agent_response["response"],
                'timestamp': get_timestamp(),
                'metadata': agent_response.get("metadata", {})
            }

            # Store and broadcast
            redis_client.rpush(chat_history_key, json.dumps(bot_message))
            socketio.emit('receive_message', bot_message, room=room_id, namespace='/api')

    except Exception as e:
        logging.error(f"Error processing message: {e}")


@app.route('/api/create_room', methods=['POST'])
def create_room():
    """Create new conversation room"""
    room_id = str(uuid.uuid4())
    # No TTL for permanent storage
    return jsonify({"room_id": room_id})

@app.route('/api/set_username', methods=['POST'])
def set_username():
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': 'Missing username in request'}), 400
        username = data['username']
        session['username'] = username
        return jsonify({'message': 'Username set successfully', 'username': username}), 200
    except Exception as e:
        logging.error(f"Error setting username: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@socketio.on('send_message', namespace='/api')
def handle_send_message(data):
    room_id = data['room_id']
    user_name = data['user_name']
    message = data['message']
    timestamp = get_timestamp()

    user_message = {'user_name': user_name, 'message': message, 'timestamp': timestamp}
    chat_history_key = f"{CHAT_HISTORY_KEY_PREFIX}{room_id}"
    redis_client.rpush(chat_history_key, json.dumps(user_message))
    emit('receive_message', user_message, room=room_id)

    # Encolar la tarea para procesar el mensaje
    task_queue.enqueue(process_message_task, room_id)

@app.route('/api/chat/<room_id>', methods=['GET'])
def get_messages(room_id: str):
    """Retrieve conversation history"""
    chat_history_key = f"{CHAT_HISTORY_KEY_PREFIX}{room_id}"
    messages = redis_client.lrange(chat_history_key, 0, -1)
    return jsonify({"messages": [json.loads(m) for m in messages]})

@app.route('/api/delete_chat/<room_id>', methods=['DELETE'])
def delete_chat(room_id: str):
    """Delete the entire chat history for a given room ID."""
    chat_history_key = f"{CHAT_HISTORY_KEY_PREFIX}{room_id}"
    if redis_client.exists(chat_history_key):
        redis_client.delete(chat_history_key)
        return jsonify({'message': f'Chat history for room {room_id} deleted successfully'}), 200
    else:
        return jsonify({'error': f'Chat history not found for room {room_id}'}), 404

@socketio.on('join', namespace='/api')
def handle_join(data):
    room_id = data['room_id']
    join_room(room_id)

@app.route('/api/simulate_message', methods=['POST'])
def simulate_message_endpoint():
    """Recibe un mensaje simulado vía HTTP y lo emite como evento de SocketIO."""
    data = request.json
    room_id = data.get('room_id')
    user_name = data.get('user_name')
    message = data.get('message')

    if not all([room_id, user_name, message]):
        abort(400)

    timestamp = get_timestamp()
    simulated_message = {'user_name': user_name, 'message': message, 'timestamp': timestamp}
    chat_history_key = f"{CHAT_HISTORY_KEY_PREFIX}{room_id}"
    redis_client.rpush(chat_history_key, json.dumps(simulated_message))
    socketio.emit('receive_message', simulated_message, room=room_id, namespace='/api')
    task_queue.enqueue(process_message_task, room_id)
    return jsonify({'status': 'Simulated message sent'}), 200

if __name__ == '__main__':
    socketio.run(app, debug=True)