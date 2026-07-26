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

@resume.route('/<int:resume_id>/delete', methods=['POST', 'DELETE'])
@login_required
def delete_resume(resume_id):
    user_id = session.get('user_id')
    res = Resume.query.filter_by(id=resume_id, user_id=user_id).first_or_404()
    
    # Clean up related analysis entries
    Analysis.query.filter_by(resume_id=resume_id).delete()
    
    db.session.delete(res)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Resume deleted successfully"
    })


@resume.route('/enhance-bullet', methods=['POST'])
@login_required
def enhance_bullet_point():
    data = request.get_json() or {}
    bullet = data.get("bullet", "")
    mode = data.get("mode", "impact")
    job_description = data.get("job_description", "")
    if not bullet:
        return jsonify({"success": False, "error": "No bullet text provided"}), 400

    enhanced = ats_analyzer.enhance_bullet(bullet, mode=mode, job_description=job_description)
    return jsonify({
        "success": True,
        "original": bullet,
        "enhanced": enhanced,
        "mode": mode
    })

@resume.route('/generate-summary', methods=['POST'])
@login_required
def generate_summary():
    data = request.get_json() or {}
    parsed_data = data.get("parsed_data", {})
    job_description = data.get("job_description", "")

    summary = ats_analyzer.generate_summary(parsed_data, job_description)
    return jsonify({
        "success": True,
        "summary": summary
    })

@resume.route('/generate-bullets', methods=['POST'])
@login_required
def generate_bullets():
    data = request.get_json() or {}
    role = data.get("role", "Software Engineer")
    company = data.get("company", "Company")
    job_description = data.get("job_description", "")

    bullets = ats_analyzer.generate_bullets_for_role(role, company, job_description)
    return jsonify({
        "success": True,
        "bullets": bullets
    })

@resume.route('/suggest-skills', methods=['POST'])
@login_required
def suggest_skills():
    data = request.get_json() or {}
    parsed_data = data.get("parsed_data", {})
    job_description = data.get("job_description", "")

    skills = ats_analyzer.suggest_skills(parsed_data, job_description)
    return jsonify({
        "success": True,
        "skills": skills
    })

@resume.route('/categorize-skills', methods=['POST'])
@login_required
def categorize_skills():
    data = request.get_json() or {}
    skills = data.get("skills", [])
    categorized = skill_manager.categorize_skill_list(skills)
    return jsonify({
        "success": True,
        "categorized": categorized
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
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0f172a'),
        alignment=1,
        spaceAfter=6
    )
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=10
    )
    sec_heading_style = ParagraphStyle(
        'SecHeadingStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=12,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor('#1e293b')
    )
    exp_title_style = ParagraphStyle(
        'ExpTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=6,
        spaceAfter=2
    )
    exp_meta_style = ParagraphStyle(
        'ExpMetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=4
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    info = parsed.get("contact_info", {})
    story.append(Paragraph(info.get("name", "Candidate"), name_style))
    
    contact_parts = []
    if info.get("email"):
        contact_parts.append(f'<a href="mailto:{info.get("email")}"><font color="#2563eb">{info.get("email")}</font></a>')
    if info.get("phone"):
        contact_parts.append(f'<a href="tel:{info.get("phone")}"><font color="#2563eb">{info.get("phone")}</font></a>')
    if info.get("location"):
        contact_parts.append(f'<b><font color="#334155">{info.get("location")}</font></b>')
    if info.get("linkedin"):
        link = info.get("linkedin")
        url = link if link.startswith("http") else f"https://{link}"
        contact_parts.append(f'<a href="{url}"><font color="#2563eb">{link}</font></a>')
    if info.get("github"):
        link = info.get("github")
        url = link if link.startswith("http") else f"https://{link}"
        contact_parts.append(f'<a href="{url}"><font color="#2563eb">{link}</font></a>')

    contact_str = ' &nbsp;<font color="#94a3b8">•</font>&nbsp; '.join(contact_parts)
    if contact_str:
        story.append(Paragraph(contact_str, contact_style))
        story.append(Spacer(1, 6))


    if parsed.get("summary"):
        story.append(Paragraph("PROFESSIONAL SUMMARY", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        story.append(Paragraph(parsed.get("summary"), body_style))
        story.append(Spacer(1, 8))

    if parsed.get("experience"):
        story.append(Paragraph("WORK EXPERIENCE", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        for exp in parsed.get("experience"):
            # Line 1: Job Title and Company
            title_str = f"<b>{exp.get('role', '')}</b>"
            if exp.get('company'):
                title_str += f" — {exp.get('company')}"
            story.append(Paragraph(title_str, exp_title_style))
            
            # Line 2: Location and Dates in BOLD on next line
            meta_parts = []
            if exp.get('location'):
                meta_parts.append(f"<b>{exp.get('location')}</b>")
            if exp.get('dates'):
                meta_parts.append(f"<b>{exp.get('dates')}</b>")
            if meta_parts:
                meta_str = " | ".join(meta_parts)
                story.append(Paragraph(meta_str, exp_meta_style))

            # Line 3+: Bullet points in larger font size
            for b in exp.get("bullets", []):
                story.append(Paragraph(f"• {b}", bullet_style))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 4))

    if parsed.get("education"):
        story.append(Paragraph("EDUCATION", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        for edu in parsed.get("education"):
            # Line 1: Degree and Institution
            edu_title = f"<b>{edu.get('degree', '')}</b>"
            if edu.get('institution'):
                edu_title += f" — {edu.get('institution')}"
            story.append(Paragraph(edu_title, exp_title_style))
            
            # Line 2: Location and Dates on NEXT line in BOLD
            edu_meta = []
            if edu.get('location'):
                edu_meta.append(f"<b>{edu.get('location')}</b>")
            if edu.get('dates'):
                edu_meta.append(f"<b>{edu.get('dates')}</b>")
            if edu_meta:
                story.append(Paragraph(" | ".join(edu_meta), exp_meta_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    skills_data = parsed.get("skills")
    if skills_data:
        story.append(Paragraph("SKILLS & TECHNICAL EXPERTISE", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        
        if isinstance(skills_data, list):
            cat_skills = skill_manager.categorize_skill_list(skills_data)
        elif isinstance(skills_data, dict):
            cat_skills = skills_data
        else:
            cat_skills = skill_manager.categorize_skill_list(str(skills_data))

        for cat_name, items in cat_skills.items():
            if not items:
                continue
            if isinstance(items, list):
                items_str = ", ".join(items)
            else:
                items_str = str(items)
            
            cat_p = f"<b>{cat_name}:</b> {items_str}"
            story.append(Paragraph(cat_p, body_style))
            story.append(Spacer(1, 3))


    doc.build(story)
    buffer.seek(0)
    
    req_filename = request.args.get('filename', '').strip()
    if req_filename:
        clean_title = re.sub(r'[^\w\-\.]', '_', req_filename)
    else:
        clean_title = re.sub(r'[^\w\-\.]', '_', res.title)

    if not clean_title.lower().endswith('.pdf'):
        download_name = f"{clean_title}.pdf"
    else:
        download_name = clean_title

    return send_file(
        buffer,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )

