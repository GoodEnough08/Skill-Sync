from flask import Blueprint, jsonify, session
from database import db
from models.user import Resume, Analysis
from routes.auth import login_required

profile = Blueprint('profile', __name__, url_prefix='/api/profile')

@profile.route('/history', methods=['GET'])
@login_required
def get_history():
    user_id = session.get('user_id')
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.created_at.desc()).all()
    history = []
    for r in resumes:
        latest = Analysis.query.filter_by(resume_id=r.id).order_by(Analysis.created_at.desc()).first()
        item = r.to_dict()
        item["ats_score"] = latest.ats_score if latest else None
        history.append(item)
    return jsonify({"success": True, "history": history})

@profile.route('/resume/<int:resume_id>', methods=['DELETE'])
@login_required
def delete_resume(resume_id):
    user_id = session.get('user_id')
    res = Resume.query.filter_by(id=resume_id, user_id=user_id).first_or_404()
    db.session.delete(res)
    db.session.commit()
    return jsonify({"success": True, "message": "Resume deleted successfully"})
