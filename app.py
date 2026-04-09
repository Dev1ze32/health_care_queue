# IMPORTS
from flask import Flask, render_template, request, jsonify, session, g
from flask_socketio import SocketIO, emit
from datetime import datetime
import qrcode
import socket
import os
import secrets
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)      # This is fine
socketio = SocketIO(app, cors_allowed_origins="*")

# Database configuration
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qms.db')

def get_db():           # reusable func
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def add_customer_history(name, phone, email, priority, service):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO customer_history
        (full_name, phone_number, email, priority_type, department)
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        phone,
        email,
        priority,
        service
    ))

    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():          # run this everytime to create database
    """Initialize database with required tables"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queue_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT NOT NULL,
                name TEXT,
                phone TEXT,
                email TEXT,
                service TEXT,
                priority TEXT,
                ip TEXT,
                joined_at TIMESTAMP,
                served_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                service_time_seconds INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone_number TEXT,
                email TEXT,
                priority_type TEXT NOT NULL,
                department TEXT NOT NULL,
                served_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

# Password magic
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash_val):
    return hash_password(password) == hash_val


# Global variables n stuff
service_times = []
MAX_SERVICE_TIMES = 20

queue = []
clients = {}
client_sids = {}
served_ctr = 0
counter = [1] 
priority_requests = {} 
current_serving = None
current_serving_start = None


# backend magic
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    s.close()
    return ip

def average_wait_time():
    if len(service_times) < 2:
        return "N/A"
    
    intervals = []
    for i in range(1, len(service_times)):
        delta = (service_times[i] - service_times[i - 1]).total_seconds()
        intervals.append(delta)
    
    avg_seconds = sum(intervals) / len(intervals)
    return f"{int(avg_seconds // 60)}m {int(avg_seconds % 60)}s"

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                      (username, hash_password(password), email))
        db.commit()
        return jsonify({"success": True, "message": "Account created successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Email already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def add_to_history(uid, service_time_seconds):
    try:
        db = get_db()
        cursor = db.cursor()

        info = clients.get(uid, {}) if isinstance(clients, dict) else {}
        name = info.get('name') if info else None
        phone = info.get('phone') if info else None
        email = info.get('email') if info else None
        service = info.get('service') if info else None
        priority = info.get('priority') if info else None
        ip = info.get('ip') if info else None
        joined_at = info.get('joined_at') if info else None

        cursor.execute('''
            INSERT INTO queue_history (
                uid, name, phone, email, service, priority, ip, joined_at, service_time_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uid, name, phone, email, service, priority, ip, joined_at, service_time_seconds))
        db.commit()

        return True
    except Exception as e:
        print(f"Error adding to history: {str(e)}")
        return False

@app.route("/login-user", methods=["POST"])
def login_user():
    data = request.json
    email = data.get("username") 
    password = data.get("password")
    print("this occurred")
    
    if not email or not password:
        print("this ocurred 2")
        return jsonify({"success": False, "message": "Email and password required"}), 400
    
    try:
        print("this ocurred 3")
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        print(f"Query result: {user}")
        print(f"Email searched: {email}")
        
        if user is None:
            print("User not found in database")
            return jsonify({"success": False, "message": "Invalid email or password"}), 401
        
        hashed_input = hash_password(password)
        stored_hash = user['password']
        print(f"Comparing hashes - Input hash: {hashed_input}, Stored hash: {stored_hash}")
        
        if hashed_input == stored_hash:
            print("this ocurred 4")
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({"success": True, "message": "Login successful"})
        else:
            print("this ocurred 5")
            return jsonify({"success": False, "message": "Invalid email or password"}), 401
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route("/home")
def home():
    if 'user_id' not in session:
        return render_template("login.html")
    return render_template("main.html")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return render_template("login.html")
    average_wait_time_seconds = average_wait_time()
    return render_template("dashboard.html", queue=queue, served_ctr=served_ctr, avt=average_wait_time_seconds)

@app.route("/reports")
def reports():
    if 'user_id' not in session:
        return render_template("login.html")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM queue_history ORDER BY served_at DESC LIMIT 30")
    queue_history = cursor.fetchall()
    cursor.execute("SELECT full_name, phone_number, email, priority_type, department, served_time" \
    " FROM customer_history ORDER BY served_time DESC LIMIT 30")
    customer_history = cursor.fetchall()
    db.close()
    average_wait_time_seconds = average_wait_time()
    queue_length = len(queue)
    return render_template("reports.html",
                            queue_history=queue_history,
                            customer_history=customer_history,
                            queue_length=queue_length,
                            served_ctr=served_ctr,
                            avt=average_wait_time_seconds,
                            total_processed=served_ctr)

@app.route("/settings")
def settings():
    if 'user_id' not in session:
        return render_template("login.html")
    return render_template("settings.html")

@app.route("/priority-requests")
def priority_requests_page():
    if 'user_id' not in session:
        return render_template("login.html")
    return render_template("priority_requests.html", requests=priority_requests)

@app.route("/about")
def about():
    if 'user_id' not in session:
        return render_template("login.html")
    return render_template("about.html")

@app.route("/display")
def display():
    if 'user_id' not in session:
        return render_template("login.html")
    ip = get_local_ip()
    url = f"http://{ip}:5002/join"

    img = qrcode.make(url)
    os.makedirs("static", exist_ok=True)
    img.save("static/qr.png")

    return render_template("display.html", queue=queue, server_ip=ip)

@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == 'GET':
        return render_template("join.html", avt=average_wait_time())

    data = request.json or {}
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    priority = data.get('priority', 'normal')
    service = data.get('service')

    uid = f"Q{counter[0]:03d}"      # somethign here is broken
    counter[0] += 1
    queue.append(uid)

    # store client this for later
    client_info = {
        'name': name,
        'phone': phone,
        'email': email,
        'priority': priority,
        'service': service,
        'ip': request.remote_addr,
        'joined_at': datetime.now().isoformat()
    }
    clients[uid] = client_info
    
    try: 
        add_customer_history(name, phone, email, priority, service)
    except Exception as e:
        print(f"Failed to add customer_history: {e}")

    print(f"New user joining with number: {uid}, total in queue: {len(queue)}")
    print(f"Current queue: {queue}, counter: {counter[0]}")

    return jsonify({"success": True, "uid": uid, "avt": average_wait_time()})

@app.route("/next")
def next_customer():
    if queue:
        global served_ctr, last_served_time
        served_ctr += 1
        current_time = datetime.now()
        service_times.append(current_time)
        
        if len(service_times) > MAX_SERVICE_TIMES + 1:
            service_times.pop(0)

        served = queue.pop(0)
        
        global current_serving, current_serving_start
        current_serving = served
        current_serving_start = current_time
        client_info_for_emit = clients.get(served)
        print(f"Emitting served for {served}, client present: {bool(client_info_for_emit)}")
        socketio.emit("served", {"uid": served, "client": client_info_for_emit})
    return ("", 204)

@app.route("/move-up", methods=["POST"])
def move_up():
    data = request.json
    uid = data.get("uid")
    
    if uid not in queue:
        return jsonify({"success": False, "message": "Customer not in queue"}), 400
    
    current_index = queue.index(uid)
    
    if current_index == 0:
        return jsonify({"success": False, "message": "Already at front of queue"}), 400

    queue[current_index - 1], queue[current_index] = queue[current_index], queue[current_index - 1]
    
    print(f"Moved {uid} up. Current queue: {queue}")
    return jsonify({"success": True, "queue": queue})


@app.route("/api/current-serving")
def api_current_serving():
    if current_serving:
        info = clients.get(current_serving, None)
        return jsonify({"uid": current_serving, "client": info})
    return jsonify({"uid": None, "client": None})


@app.route('/api/client/<uid>')
def api_client_info(uid):
    info = clients.get(uid)
    if info:
        return jsonify(info)
    return jsonify({})


@app.route("/complete", methods=["POST"])
def complete_service():
    global current_serving, current_serving_start
    if not current_serving:
        return jsonify({"success": False, "message": "No current serving customer"}), 400

    now = datetime.now()
    service_time_seconds = int((now - (current_serving_start or now)).total_seconds())
    try:
        add_to_history(current_serving, service_time_seconds)
    except Exception as e:
        print(f"Error finalizing history for {current_serving}: {e}")
    try:
        if current_serving in clients:
            del clients[current_serving]
    except Exception:
        pass

    current_serving = None
    current_serving_start = None
    return jsonify({"success": True})


@app.route("/recall", methods=["POST"])
def recall_customer():
    if not current_serving:
        return jsonify({"success": False, "message": "No current serving customer"}), 400
    print(f"Re-emitting served for {current_serving}, client present: {bool(clients.get(current_serving))}")
    socketio.emit("served", {"uid": current_serving, "client": clients.get(current_serving)})
    return jsonify({"success": True})


@app.route("/no-show", methods=["POST"])
def no_show():
    global current_serving, current_serving_start
    if not current_serving:
        return jsonify({"success": False, "message": "No current serving customer"}), 400

    try:
        add_to_history(current_serving, 0)
    except Exception as e:
        print(f"Error recording no-show for {current_serving}: {e}")

    try:
        if current_serving in clients:
            del clients[current_serving]
    except Exception:
        pass

    current_serving = None
    current_serving_start = None
    return jsonify({"success": True})

@app.route("/request-priority", methods=["POST"])
def request_priority():
    data = request.json
    uid = data.get("uid")
    new_position = data.get("position")
    
    if uid not in queue or new_position is None:
        return jsonify({"success": False, "message": "Invalid request"}), 400
    
    new_position = int(new_position)
    if new_position < 0 or new_position >= len(queue):
        return jsonify({"success": False, "message": "Invalid position"}), 400
    

    priority_requests[uid] = new_position
    print(f"{uid} requested to move to position {new_position}")
    
    return jsonify({"success": True, "message": "Request submitted for admin approval"})

@app.route("/api/priority-requests")
def get_priority_requests():
    return jsonify({"requests": priority_requests})

@app.route("/api/queue-count")
def get_queue_count():
    return jsonify({"count": len(queue)})

@app.route("/approve-priority", methods=["POST"])
def approve_priority():
    data = request.json
    uid = data.get("uid")
    approve = data.get("approve", True)
    
    if uid not in priority_requests:
        return jsonify({"success": False, "message": "Request not found"}), 400
    
    if approve:
        new_position = priority_requests[uid]
        if uid in queue:
            queue.remove(uid)
            queue.insert(min(new_position, len(queue)), uid)
            print(f"Approved: Moved {uid} to position {new_position}. Current queue: {queue}")
    
    del priority_requests[uid]
    
    return jsonify({"success": True, "queue": queue})

@socketio.on("register")
def register(data):
    client_sids[data["uid"]] = request.sid

@socketio.on("connect")
def on_connect():
    print("Client connected")

@socketio.on("disconnect")
def on_disconnect():
    print("Client disconnected")
    try:
        to_remove = [uid for uid, sid in client_sids.items() if sid == request.sid]
        for uid in to_remove:
            del client_sids[uid]
    except Exception:
        pass


if __name__ == "__main__":
    ip = get_local_ip()
    # Correct the print statement to match the actual port
    print(f"The server is active at http://{ip}:5002/login")
    init_db()
    socketio.run(app, host="0.0.0.0", port=5002, debug=True, allow_unsafe_werkzeug=True)