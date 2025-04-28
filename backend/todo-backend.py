import os
import time
import psycopg2
import logging
import asyncio
from flask import Flask, request, jsonify
from nats.aio.client import Client as NATS

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# NATS setup
nats_url = os.getenv("NATS_URL", "nats://my-nats:4222")
nc = NATS()
nats_ready = False

async def connect_nats():
    global nats_ready
    while not nats_ready:
        try:
            await nc.connect(servers=[nats_url])
            logging.info("✅ Connected to NATS!")
            nats_ready = True
        except Exception as e:
            logging.warning(f"❌ NATS not ready, retrying... {e}")
            await asyncio.sleep(2)

# Initial hardcoded todos
initial_todos = [
    "Buy groceries",
    "Walk the dog",
    "Finish the project",
    "Read a book"
]

def get_db_connection():
    while True:
        try:
            conn = psycopg2.connect(
                host=os.environ.get("DB_HOST", "localhost"),
                port=os.environ.get("DB_PORT", 5432),
                database=os.environ["POSTGRES_DB"],
                user=os.environ["POSTGRES_USER"],
                password=os.environ["POSTGRES_PASSWORD"]
            )
            return conn
        except Exception as e:
            logging.warning(f"DB not ready, retrying... {e}")
            time.sleep(2)

def initialize_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        );
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM todos;")
    count = cur.fetchone()[0]

    if count == 0:
        for todo in initial_todos:
            cur.execute("INSERT INTO todos (content) VALUES (%s);", (todo,))
        conn.commit()

    return conn

# Initialize connection and table
conn = initialize_db()

async def publish_nats_message(subject, message):
    if nats_ready:
        try:
            await nc.publish(subject, message.encode())
            logging.info(f"📤 Published to NATS: {message}")
        except Exception as e:
            logging.warning(f"❌ Failed to publish to NATS: {e}")

def safe_create_task(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.create_task(coro)

@app.route("/todos", methods=["GET", "POST"])
def handle_todos():
    cur = conn.cursor()

    if request.method == "POST":
        data = request.get_json()
        new_todo = data.get("todo")

        if not new_todo:
            logging.warning("[POST] Missing 'todo' in request")
            return jsonify({"error": "Missing 'todo' in request body"}), 400

        if len(new_todo) > 140:
            logging.warning(f"[POST] Rejected todo over 140 characters: {new_todo}")
            return jsonify({"error": "Todo exceeds 140 characters"}), 400

        logging.info(f"[POST] New todo received: {new_todo}")
        cur.execute("INSERT INTO todos (content) VALUES (%s);", (new_todo,))
        conn.commit()

        # Publish event asynchronously
        safe_create_task(publish_nats_message("todo.updates", f"New todo created: {new_todo}"))

        cur.execute("SELECT id, content, done FROM todos;")
        result = cur.fetchall()
        return jsonify({"message": "Todo added", "todos": [{"id": row[0], "content": row[1], "done": row[2]} for row in result]}), 201

    if request.method == "GET":
        logging.info("[GET] Fetching todos")
        cur.execute("SELECT id, content, done FROM todos;")
        result = cur.fetchall()
        return jsonify([{"id": row[0], "content": row[1], "done": row[2]} for row in result])

@app.route("/todos/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id):
    data = request.get_json()
    done_status = data.get("done")

    if done_status is None:
        return jsonify({"error": "'done' field is required"}), 400

    try:
        cur = conn.cursor()
        cur.execute("UPDATE todos SET done = %s WHERE id = %s;", (done_status, todo_id))
        conn.commit()

        # Publish event asynchronously
        safe_create_task(publish_nats_message("todo.updates", f"Todo {todo_id} marked as done: {done_status}"))

        cur.execute("SELECT id, content, done FROM todos;")
        updated_todos = cur.fetchall()

        todos_list = [{"id": row[0], "content": row[1], "done": row[2]} for row in updated_todos]
        return jsonify({"message": "Todo updated", "todos": todos_list})
    except Exception as e:
        return jsonify({"error": f"Update failed: {e}"}), 500

@app.route("/healthz")
def healthz():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", 5432),
            database=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"]
        )
        conn.close()
        return "OK", 200
    except Exception as e:
        return f"Database connection failed: {e}", 503

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(connect_nats())
    app.run(host="0.0.0.0", port=3001)
