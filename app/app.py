import json
from app.llm.chat_agent import evaluate_and_respond
from flask import Flask, abort, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import redis
import uuid
import random
import time

SECONDS_TO_RESPOND = 20

app = Flask(__name__)
socketio = SocketIO(app)
socketio.init_app(app, cors_allowed_origins="*")
CORS(app)


r = redis.Redis(host='localhost', port=6379, db=0)

def generate_anonymous_name():
    return f"User{random.randint(1000, 9999)}"

@app.route('/api/create_room', methods=['POST'])
def create_room_api():
    room_id = str(uuid.uuid4())
    room_exists = r.get(f'room_{room_id}')
    if room_exists is not None:
      abort(404)
    r.set(f'room_{room_id}', 1)
    return jsonify({'room_id': room_id})


@socketio.on('send_message')
def handle_send_message(data):
    room_id = data['room_id']
    user_name = data['user_name']
    message = data['message']
    user_message = {'user_name': user_name, 'message': message}
    
    
    r.rpush(room_id, json.dumps(user_message))
    # Emitir el mensaje del usuario al room
    emit('receive_message', user_message, room=room_id)
   
    
    # Recuperar últimos 10 mensajes del room
    raw_messages = r.lrange(room_id, -10, -1)
    messages = [json.loads(msg) for msg in raw_messages]
    
    # Comprobar si han pasado 20 segundos desde la última respuesta del bot
    last_bot_response_time_key = f"last_bot_response_time_{room_id}"
    current_time = time.time()
    last_response_time = r.get(last_bot_response_time_key)

    if last_response_time:
        last_response_time = float(last_response_time)
        if current_time - last_response_time < SECONDS_TO_RESPOND:
            # No responder si no han pasado 20 segundos
            return
    
    # Evaluar si el bot debe responder y generar respuesta
    evaluation = evaluate_and_respond(messages)
    
    if evaluation["should_react"]:
        bot_message = {'user_name': 'Bot', 'message': evaluation["response"]}
        emit('receive_message', bot_message, room=room_id)
        r.rpush(room_id, json.dumps(bot_message))
        
        # Actualizar el tiempo de la última respuesta del bot
        r.set(last_bot_response_time_key, current_time)

@socketio.on('join')
def handle_join(data):
    room_id = data['room_id']
    join_room(room_id)

@app.route('/api/chat/<room_id>', methods=['GET'])
def get_messages(room_id):
    raw_messages = r.lrange(room_id, 0, -1)
    room_exists = r.get(f'room_{room_id}')
    if not raw_messages and room_exists is None:
        abort(404)
    messages = [json.loads(msg) for msg in raw_messages]
    user_name = generate_anonymous_name()
    return jsonify({'messages': messages, 'user_name': user_name})

def generate_bot_response(message):
    return f"Gracias por tu mensaje: {message}"

if __name__ == '__main__':
    socketio.run(app, debug=True)
