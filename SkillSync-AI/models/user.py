from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resumes = db.relationship('Resume', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Resume(db.Model):
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False, default="Untitled Resume")
    original_filename = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(50), nullable=True)
    parsed_data = db.Column(db.Text, nullable=True)  # JSON string
    full_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    analyses = db.relationship('Analysis', backref='resume', lazy=True, cascade="all, delete-orphan")

    def get_parsed_data(self):
        if self.parsed_data:
            try:
                return json.loads(self.parsed_data)
            except Exception:
                return {}
        return {}

    def set_parsed_data(self, data):
        self.parsed_data = json.dumps(data)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "parsed_data": self.get_parsed_data(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Analysis(db.Model):
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_title = db.Column(db.String(255), nullable=True)
    job_description = db.Column(db.Text, nullable=True)
    ats_score = db.Column(db.Float, default=0.0)
    structure_score = db.Column(db.Float, default=0.0)
    keyword_score = db.Column(db.Float, default=0.0)
    impact_score = db.Column(db.Float, default=0.0)
    verb_score = db.Column(db.Float, default=0.0)
    missing_skills = db.Column(db.Text, nullable=True)  # JSON list
    matched_skills = db.Column(db.Text, nullable=True)  # JSON list
    feedback = db.Column(db.Text, nullable=True)        # JSON dict/list
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "job_title": self.job_title or "",
            "job_description": self.job_description or "",
            "ats_score": round(self.ats_score, 1),
            "structure_score": round(self.structure_score, 1),
            "keyword_score": round(self.keyword_score, 1),
            "impact_score": round(self.impact_score, 1),
            "verb_score": round(self.verb_score, 1),
            "missing_skills": json.loads(self.missing_skills) if self.missing_skills else [],
            "matched_skills": json.loads(self.matched_skills) if self.matched_skills else [],
            "feedback": json.loads(self.feedback) if self.feedback else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
