import json
from flask import Flask, abort, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import redis
import uuid
import random

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
    
    user_message =  {'user_name': user_name, 'message': message}
    emit('receive_message', user_message, room=room_id) 

    bot_response = generate_bot_response(message)
    
    r.rpush(room_id, json.dumps(user_message))
    
    bot_message = {'user_name': 'Bot', 'message': bot_response}

    emit('receive_message', bot_message, room=room_id)
    
    r.rpush(room_id, json.dumps(bot_message))

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
