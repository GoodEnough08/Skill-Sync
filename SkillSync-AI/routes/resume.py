import os
import json
from flask import Blueprint, request, jsonify, current_app, send_file, session
from werkzeug.utils import secure_filename
from database import db
from models.user import Resume, Analysis
from ai.parser import ResumeParser
from ai.ats import ATSAnalyzer
from ai.skills import SkillManager
from routes.auth import login_required
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

resume = Blueprint('resume', __name__, url_prefix='/api/resume')

parser = ResumeParser()
ats_analyzer = ATSAnalyzer()
skill_manager = SkillManager()

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@resume.route('/upload', methods=['POST'])
@login_required
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        job_description = request.form.get('job_description', '')
        job_title = request.form.get('job_title', '')

        try:
            raw_text = parser.extract_text(file_path)
            parsed_data = parser.parse(raw_text)

            candidate_name = parsed_data.get("contact_info", {}).get("name") or "Candidate"
            title = f"{candidate_name}'s Resume"

            new_resume = Resume(
                user_id=session.get('user_id'),
                title=title,
                original_filename=filename,
                file_type=os.path.splitext(filename)[1].lower(),
                parsed_data=json.dumps(parsed_data),
                full_text=raw_text
            )
            db.session.add(new_resume)
            db.session.commit()

            # Run baseline ATS analysis
            analysis_result = ats_analyzer.analyze(parsed_data, job_description)
            
            new_analysis = Analysis(
                resume_id=new_resume.id,
                job_title=job_title,
                job_description=job_description,
                ats_score=analysis_result["ats_score"],
                structure_score=analysis_result["structure_score"],
                keyword_score=analysis_result["keyword_score"],
                impact_score=analysis_result["impact_score"],
                verb_score=analysis_result["verb_score"],
                missing_skills=json.dumps(analysis_result["skill_gap"]["missing_skills"]),
                matched_skills=json.dumps(analysis_result["skill_gap"]["matched_skills"]),
                feedback=json.dumps(analysis_result["feedback"])
            )
            db.session.add(new_analysis)
            db.session.commit()

            return jsonify({
                "success": True,
                "resume_id": new_resume.id,
                "parsed_data": parsed_data,
                "analysis": analysis_result
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": False, "error": "Invalid file format. Supported formats: PDF, DOCX, TXT"}), 400

@resume.route('/<int:resume_id>', methods=['GET'])
@login_required
def get_resume(resume_id):
    user_id = session.get('user_id')
    res = Resume.query.filter_by(id=resume_id, user_id=user_id).first_or_404()
    latest_analysis = Analysis.query.filter_by(resume_id=resume_id).order_by(Analysis.created_at.desc()).first()
    
    parsed_data = res.get_parsed_data()
    analysis_data = latest_analysis.to_dict() if latest_analysis else ats_analyzer.analyze(parsed_data)

    return jsonify({
        "success": True,
        "resume": res.to_dict(),
        "analysis": analysis_data
    })

@resume.route('/<int:resume_id>/update', methods=['POST'])
@login_required
def update_resume(resume_id):
    user_id = session.get('user_id')
    res = Resume.query.filter_by(id=resume_id, user_id=user_id).first_or_404()
    req_data = request.get_json()
    
    if not req_data or "parsed_data" not in req_data:
        return jsonify({"success": False, "error": "Missing parsed_data"}), 400

    parsed_data = req_data["parsed_data"]
    res.set_parsed_data(parsed_data)

    if "title" in req_data and req_data["title"]:
        res.title = req_data["title"]

    job_description = req_data.get("job_description", "")
    analysis_result = ats_analyzer.analyze(parsed_data, job_description)

    new_analysis = Analysis(
        resume_id=res.id,
        job_title=req_data.get("job_title", ""),
        job_description=job_description,
        ats_score=analysis_result["ats_score"],
        structure_score=analysis_result["structure_score"],
        keyword_score=analysis_result["keyword_score"],
        impact_score=analysis_result["impact_score"],
        verb_score=analysis_result["verb_score"],
        missing_skills=json.dumps(analysis_result["skill_gap"]["missing_skills"]),
        matched_skills=json.dumps(analysis_result["skill_gap"]["matched_skills"]),
        feedback=json.dumps(analysis_result["feedback"])
    )
    db.session.add(new_analysis)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Resume updated successfully",
        "resume": res.to_dict(),
        "analysis": analysis_result
    })

@resume.route('/<int:resume_id>/analyze-jd', methods=['POST'])
@login_required
def analyze_job_description(resume_id):
    user_id = session.get('user_id')
    res = Resume.query.filter_by(id=resume_id, user_id=user_id).first_or_404()
    req_data = request.get_json() or {}
    job_description = req_data.get("job_description", "")
    job_title = req_data.get("job_title", "")

    parsed_data = res.get_parsed_data()
    analysis_result = ats_analyzer.analyze(parsed_data, job_description)

    new_analysis = Analysis(
        resume_id=res.id,
        job_title=job_title,
        job_description=job_description,
        ats_score=analysis_result["ats_score"],
        structure_score=analysis_result["structure_score"],
        keyword_score=analysis_result["keyword_score"],
        impact_score=analysis_result["impact_score"],
        verb_score=analysis_result["verb_score"],
        missing_skills=json.dumps(analysis_result["skill_gap"]["missing_skills"]),
        matched_skills=json.dumps(analysis_result["skill_gap"]["matched_skills"]),
        feedback=json.dumps(analysis_result["feedback"])
    )
    db.session.add(new_analysis)
    db.session.commit()

    return jsonify({
        "success": True,
        "analysis": analysis_result
    })

@resume.route('/enhance-bullet', methods=['POST'])
@login_required
def enhance_bullet_point():
    data = request.get_json() or {}
    bullet = data.get("bullet", "")
    if not bullet:
        return jsonify({"success": False, "error": "No bullet text provided"}), 400

    enhanced = ats_analyzer.enhance_bullet(bullet)
    return jsonify({
        "success": True,
        "original": bullet,
        "enhanced": enhanced
    })

@resume.route('/<int:resume_id>/export/pdf', methods=['GET'])
@login_required
def export_pdf(resume_id):
    user_id = session.get('user_id')
    res = Resume.query.filter_by(id=resume_id, user_id=user_id).first_or_404()
    parsed = res.get_parsed_data()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle(
        'NameStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        alignment=1
    )
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )
    sec_heading_style = ParagraphStyle(
        'SecHeadingStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#334155'),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    info = parsed.get("contact_info", {})
    story.append(Paragraph(info.get("name", "Candidate"), name_style))
    
    contact_parts = [info.get("email", ""), info.get("phone", ""), info.get("location", ""), info.get("linkedin", ""), info.get("github", "")]
    contact_str = " • ".join([c for c in contact_parts if c])
    if contact_str:
        story.append(Paragraph(contact_str, contact_style))
        story.append(Spacer(1, 10))

    if parsed.get("summary"):
        story.append(Paragraph("PROFESSIONAL SUMMARY", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        story.append(Paragraph(parsed.get("summary"), body_style))
        story.append(Spacer(1, 8))

    if parsed.get("experience"):
        story.append(Paragraph("WORK EXPERIENCE", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        for exp in parsed.get("experience"):
            title_str = f"<b>{exp.get('role', '')}</b> — {exp.get('company', '')}"
            if exp.get('dates'):
                title_str += f" ({exp.get('dates')})"
            story.append(Paragraph(title_str, body_style))
            for b in exp.get("bullets", []):
                story.append(Paragraph(f"• {b}", bullet_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    if parsed.get("education"):
        story.append(Paragraph("EDUCATION", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        for edu in parsed.get("education"):
            edu_str = f"<b>{edu.get('degree', '')}</b> — {edu.get('institution', '')}"
            if edu.get('dates'):
                edu_str += f" ({edu.get('dates')})"
            story.append(Paragraph(edu_str, body_style))
        story.append(Spacer(1, 8))

    skills_data = parsed.get("skills")
    if skills_data:
        story.append(Paragraph("SKILLS", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        if isinstance(skills_data, list):
            skills_str = ", ".join(skills_data)
        elif isinstance(skills_data, dict):
            flat = skill_manager.flatten_skills(skills_data)
            skills_str = ", ".join(flat)
        else:
            skills_str = str(skills_data)
        story.append(Paragraph(skills_str, body_style))

    doc.build(story)
    buffer.seek(0)
    
    clean_title = res.title.replace(' ', '_')
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{clean_title}.pdf",
        mimetype='application/pdf'
    )
