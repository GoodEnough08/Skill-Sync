import os
from flask import Flask
from database import db

from routes.main import main
from routes.resume import resume
from routes.profile import profile
from routes.auth import auth

app = Flask(__name__)

app.config["SECRET_KEY"] = "skillsync-ai-secret-key-2026-auth"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///skillsync.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload limit

os.makedirs(os.path.join(app.root_path, 'uploads'), exist_ok=True)

db.init_app(app)

app.register_blueprint(main)
app.register_blueprint(auth)
app.register_blueprint(resume)
app.register_blueprint(profile)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)