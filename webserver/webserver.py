import os
import time
import requests
from flask import Flask, render_template, request, redirect, url_for

# Environment/config
PORT = int(os.getenv("PORT", 5000))
IMAGE_CACHE_PATH = "/usr/src/app/static/cache_image.jpg"
CACHE_EXPIRATION_TIME = 60 * 60  # 1 hour
TODO_API_URL = os.getenv("TODO_API_URL", "http://localhost:5001/todos")  # URL of the todo backend

# Flask app
app = Flask(__name__)

# Ensure image cache directory exists
os.makedirs(os.path.dirname(IMAGE_CACHE_PATH), exist_ok=True)

def fetch_and_cache_image():
    if not os.path.exists(IMAGE_CACHE_PATH) or is_image_cache_expired():
        print("Fetching a new image...")
        response = requests.get("https://picsum.photos/1200")
        if response.status_code == 200:
            with open(IMAGE_CACHE_PATH, "wb") as f:
                f.write(response.content)
        else:
            print("Failed to fetch image from Lorem Picsum")
    else:
        print("Using cached image.")

def is_image_cache_expired():
    if not os.path.exists(IMAGE_CACHE_PATH):
        return True
    file_mod_time = os.path.getmtime(IMAGE_CACHE_PATH)
    return (time.time() - file_mod_time) > CACHE_EXPIRATION_TIME

@app.route("/", methods=["GET", "POST"])
def home():
    fetch_and_cache_image()

    if request.method == "POST":
        if "todo" in request.form:
            new_todo = request.form.get("todo")
            if new_todo:
                try:
                    response = requests.post(TODO_API_URL, json={"todo": new_todo})
                    response.raise_for_status()
                except Exception as e:
                    print(f"Error adding todo: {e}")

        elif "done_id" in request.form:
            done_id = request.form.get("done_id")
            try:
                response = requests.put(f"{TODO_API_URL}/{done_id}", json={"done": True})
                response.raise_for_status()
            except Exception as e:
                print(f"Error marking todo as done: {e}")

        return redirect(url_for("home"))

    try:
        todo_response = requests.get(TODO_API_URL)
        todo_response.raise_for_status()
        todos = todo_response.json()
    except Exception as e:
        print(f"Error fetching todos: {e}")
        todos = [f"Error loading todos: {e}"]

    return render_template("welcome.html", image_filename="cache_image.jpg", todos=todos)

if __name__ == "__main__":
    print(f"Server started on port {PORT}", flush=True)
    app.run(host="0.0.0.0", port=PORT)