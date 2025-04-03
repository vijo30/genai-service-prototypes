import json
import logging
import os
import uuid
from datetime import datetime

from requests import session
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
        raw_messages = redis_client.lrange(room_id, -CONVERSATION_WINDOW, -1)
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
            redis_client.rpush(room_id, json.dumps(bot_message))
            socketio.emit('receive_message', bot_message, room=room_id, namespace='/api')
            

    except Exception as e:
        logging.error(f"Error processing message: {e}")


@app.route('/api/create_room', methods=['POST'])
def create_room():
    """Create new conversation room"""
    room_id = str(uuid.uuid4())
    redis_client.set(f"room:{room_id}", "active", ex=86400)  # 24h TTL
    return jsonify({"room_id": room_id})

@app.route('/api/set_username', methods=['POST'])
def set_username():
    data = request.json
    session['username'] = data.get('username', 'Anonymous')
    return jsonify({'message': 'Username set successfully', 'username': session['username']}), 200

@socketio.on('send_message', namespace='/api')
def handle_send_message(data):
    room_id = data['room_id']
    user_name = data['user_name']
    message = data['message']
    timestamp = get_timestamp()

    user_message = {'user_name': user_name, 'message': message, 'timestamp': timestamp}
    redis_client.rpush(room_id, json.dumps(user_message))
    emit('receive_message', user_message, room=room_id)



    # Encolar la tarea para procesar el mensaje
    task_queue.enqueue(process_message_task, room_id)

            

    
    


@app.route('/api/chat/<room_id>', methods=['GET'])
def get_messages(room_id: str):
    """Retrieve conversation history"""
    if not redis_client.exists(f"room:{room_id}"):
        abort(404)
    
    messages = redis_client.lrange(room_id, 0, -1)
    return jsonify({"messages": [json.loads(m) for m in messages]})

@socketio.on('join', namespace='/api')
def handle_join(data):
    room_id = data['room_id']
    join_room(room_id)

if __name__ == '__main__':
    socketio.run(app, debug=True)
