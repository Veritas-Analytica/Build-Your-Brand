from flask import Flask, render_template, request, jsonify, redirect, url_for
import yaml
import subprocess
from flask import Response
from openai import OpenAI
import json
import time
import threading
from flask_socketio import SocketIO

app = Flask(__name__)
app = Flask(__name__, template_folder= 'templates')
socketio = SocketIO(app)
# Load the YAML configuration file
with open("config.yaml", "r", encoding='utf-8') as file:
    config = yaml.safe_load(file)

# Access the variables
openai_api_key = config["openai_api_key"]

# Initialize the OpenAI client
client = OpenAI(
    api_key=openai_api_key,  # Replace with your API key if not using environment variable
)

# Load config.yaml
CONFIG_FILE = 'config.yaml'


def run_command(command, command_id):
    """Run a shell command and emit output in real time."""
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    for line in process.stdout:
        socketio.emit('command_output', {'command_id': command_id, 'output': line.strip()}, to=None)
    process.stdout.close()
    process.wait()



@socketio.on('run_commands')
def handle_run_commands(data):
    """Handle running multiple commands."""
    commands = data.get('commands', [])
    for idx, command in enumerate(commands):
        threading.Thread(target=run_command, args=(command, idx)).start()


def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def save_config(config_data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        yaml.dump(config_data, file)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get data from form
        character_name = request.form.get('character_name')
        twitter_username = request.form.get('twitter_username')
        twitter_password = request.form.get('twitter_password')
        twitter_email = request.form.get('twitter_email')

        # Load and update YAML config
        config = load_config()
        config['character_name'] = character_name
        config['twitter'] = {
            'username': twitter_username,
            'password': twitter_password,
            'email': twitter_email,
        }
        save_config(config)
        return redirect(url_for('generate_character'))

    return render_template('index.html')

def read_json_file(file_path):
    """Reads the content of a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

@app.route('/generate-character', methods=['GET'])
def generate_character():
    """Render the page with an animation."""
    return render_template('generate_character.html')

@app.route('/generate-character-api', methods=['POST'])
def generate_character_api():
    """API to generate a new character profile."""
    # Path to the original character JSON file
    input_file = 'characters/trump.character.json'

    # Read the existing character profile
    with open(input_file, 'r', encoding='utf-8') as f:
        original_character = json.load(f)

    # Load the YAML configuration file
    with open("config.yaml", "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    # Access the variables
    name = config["character_name"]

    # Uses OpenAI's GPT-4 to generate a new character profile
    prompt = (
        f"Given the following character profile:\n\n"
        f"{json.dumps(original_character, indent=2)}\n\n"
        f"Generate a similar character profile for {name} in JSON format. Client should be of Twitter only."
    )

    # Call the OpenAI API (replace `client` with your OpenAI client)
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
    )

    content = response.choices[0].message.content

    # Extract the JSON block from the response
    start_index = content.find("```json") + len("```json")
    end_index = content.find("```", start_index)
    json_str = content[start_index:end_index].strip()

    try:
        # Parse the JSON string
        json_data = json.loads(json_str)

        # Save to a file
        output_file = f"characters/{name.lower().replace(' ', '_')}.character.json"
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)

        return jsonify({"success": True})

    except json.JSONDecodeError as e:
        return jsonify({"success": False, "error": f"Error parsing JSON: {e}"})

@app.route('/terminals')
def terminals():
    """Serve the main page."""
    return render_template('terminals.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)