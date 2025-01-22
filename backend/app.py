import json
import os
import uuid
from datetime import datetime
from flask import Flask, abort, session, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import redis
from redis import from_url
from rq import Queue
from rq.job import Job
from dotenv import load_dotenv
from llm.chat_agent import manage_agents

# Cargar configuraciones
load_dotenv()

ORIGIN_DOMAIN = os.getenv("ORIGIN_DOMAIN")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

app = Flask(__name__)
app.secret_key = "your_secret_key"
CORS(app, resources={r"/*": {"origins": [f"https://{ORIGIN_DOMAIN}", "http://localhost:3000"]}})
socketio = SocketIO(app, async_mode='eventlet', message_queue=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}", cors_allowed_origins=[f"https://{ORIGIN_DOMAIN}", "http://localhost:3000"])

# Configuración de Redis y la cola
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False, db=REDIS_DB)
queue = Queue(connection=r)


def __get_redis_con():
    return r

def __get_queue():
    return queue
    
def __sheduled_tasks_count(queue_name='default'):
    queue = __get_queue()
    return queue.count
    
def __add_task_to_queue(task,*args,**kwargs):
    queue = __get_queue()
    queue.enqueue(task,*args,**kwargs)    

def __finished_tasks():
    conn = __get_redis_con()
    queue = __get_queue()
    job_ids=queue.finished_job_registry.get_job_ids()
    _jobs=[Job.fetch(_job_id, connection=conn) for _job_id in job_ids]
    return _jobs     

def get_timestamp():
    """Generar un timestamp estandarizado."""
    return datetime.utcnow().isoformat() + "Z"  # UTC

def process_message(room_id):
    """Procesa el mensaje y genera la respuesta del bot si es necesario."""
    # Obtener la conversación completa
    conversation = [json.loads(msg) for msg in r.lrange(room_id, -10, -1)]

    # Obtener respuesta del moderador
    moderator_response = manage_agents(conversation)

    if moderator_response["should_react"]:
        bot_message = {
            'user_name': 'Bot',
            'message': moderator_response["response"],
            'timestamp': get_timestamp()
        }
        r.rpush(room_id, json.dumps(bot_message))
        socketio.emit('receive_message', bot_message, room=room_id, namespace='/api')
        return bot_message

    return None


@app.route('/api/create_room', methods=['POST'])
def create_room_api():
    room_id = str(uuid.uuid4())
    room_exists = r.get(f'room_{room_id}')
    if room_exists is not None:
        abort(404)
    r.set(f'room_{room_id}', 1)
    return jsonify({'room_id': room_id})

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
    r.rpush(room_id, json.dumps(user_message))
    emit('receive_message', user_message, room=room_id)



    # Encolar la tarea para procesar el mensaje
    __add_task_to_queue(process_message, room_id)

            

    
    


@app.route('/api/chat/<room_id>', methods=['GET'])
def get_messages(room_id):
    raw_messages = r.lrange(room_id, 0, -1)
    room_exists = r.get(f'room_{room_id}')
    if not raw_messages and room_exists is None:
        abort(404)
    messages = [json.loads(msg) for msg in raw_messages]
    return jsonify({'messages': messages})

@socketio.on('join', namespace='/api')
def handle_join(data):
    room_id = data['room_id']
    join_room(room_id)

if __name__ == '__main__':
    socketio.run(app, debug=True)
