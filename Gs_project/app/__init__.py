from flask import Flask
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'standaard_geheime_sleutel')
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

# Maak de uploads map aan als deze nog niet bestaat
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

from app import routes