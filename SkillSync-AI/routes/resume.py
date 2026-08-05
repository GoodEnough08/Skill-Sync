import os
import json
import re
from flask import Blueprint, request, jsonify, current_app, send_file, session

from werkzeug.utils import secure_filename
from database import db
from models.user import Resume, Analysis
from ai.parser import ResumeParser
from ai.ats import ATSAnalyzer
from ai.skills import SkillManager
from ai.generator import PromptResumeGenerator
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
prompt_generator = PromptResumeGenerator()

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

@resume.route('/generate-from-prompt', methods=['POST'])
def generate_from_prompt():
    """Generates a structured resume JSON from prompt text and template choice."""
    data = request.get_json() or {}
    prompt_text = data.get("prompt", "")
    target_role = data.get("target_role", "")
    exp_level = data.get("exp_level", "Mid-Level")
    job_description = data.get("job_description", "")
    template_id = data.get("template_id", "modern-tech")

    if not prompt_text and not target_role:
        return jsonify({"success": False, "error": "Please provide a prompt or target role."}), 400

    try:
        parsed_data = prompt_generator.generate_from_prompt(
            prompt=prompt_text,
            target_role=target_role,
            exp_level=exp_level,
            job_description=job_description
        )

        analysis_result = ats_analyzer.analyze(parsed_data, job_description)

        return jsonify({
            "success": True,
            "parsed_data": parsed_data,
            "analysis": analysis_result,
            "template_id": template_id,
            "message": "Resume successfully generated from prompt!"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@resume.route('/save-generated', methods=['POST'])
@login_required
def save_generated_resume():
    """Saves an AI-generated or template-built resume to the logged-in user's profile."""
    data = request.get_json() or {}
    parsed_data = data.get("parsed_data")
    if not parsed_data:
        return jsonify({"success": False, "error": "Missing parsed_data"}), 400

    candidate_name = parsed_data.get("contact_info", {}).get("name") or "Candidate"
    title = data.get("title") or f"{candidate_name}'s AI Resume"
    job_description = data.get("job_description", "")
    job_title = data.get("job_title", "")

    try:
        raw_text = parsed_data.get("raw_text", "") or ats_analyzer._build_full_text_from_parsed(parsed_data)
        
        new_resume = Resume(
            user_id=session.get('user_id'),
            title=title,
            original_filename="AI_Generated_Resume.json",
            file_type=".json",
            parsed_data=json.dumps(parsed_data),
            full_text=raw_text
        )
        db.session.add(new_resume)
        db.session.commit()

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
            "message": "Resume successfully saved to your account!",
            "resume": new_resume.to_dict()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def build_template_pdf_story(parsed, template_id="modern-tech", accent_hex="#2563eb"):
    import re
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    font_name = 'Times-Roman' if template_id == 'executive-elite' else 'Helvetica'
    font_bold = 'Times-Bold' if template_id == 'executive-elite' else 'Helvetica-Bold'

    heading_color = colors.HexColor(accent_hex if accent_hex and accent_hex != 'undefined' else '#1e40af')
    if template_id == 'executive-elite':
        heading_color = colors.HexColor('#b45309')
    elif template_id == 'minimalist-clean':
        heading_color = colors.HexColor('#059669')
    elif template_id == 'creative-prof':
        heading_color = colors.HexColor('#6366f1')

    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle(
        'NameStyle',
        parent=styles['Heading1'],
        fontName=font_bold,
        fontSize=24 if template_id == 'executive-elite' else 22,
        leading=28,
        textColor=colors.HexColor('#0f172a'),
        alignment=1 if template_id in ['executive-elite', 'ats-formal', 'modern-tech'] else 0,
        spaceAfter=4
    )
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1 if template_id in ['executive-elite', 'ats-formal', 'modern-tech'] else 0,
        spaceAfter=10
    )
    sec_heading_style = ParagraphStyle(
        'SecHeadingStyle',
        parent=styles['Heading2'],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=heading_color,
        spaceBefore=12,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor('#1e293b')
    )
    exp_title_style = ParagraphStyle(
        'ExpTitleStyle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=5,
        spaceAfter=2
    )
    exp_meta_style = ParagraphStyle(
        'ExpMetaStyle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=9.5,
        leading=13,
        textColor=heading_color,
        spaceAfter=4
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14.5,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    info = parsed.get("contact_info", {})
    story.append(Paragraph(info.get("name", "Candidate"), name_style))
    
    contact_parts = []
    if info.get("email"):
        contact_parts.append(f'<a href="mailto:{info.get("email")}"><font color="{heading_color.hexval()}">{info.get("email")}</font></a>')
    if info.get("phone"):
        contact_parts.append(f'{info.get("phone")}')
    if info.get("location"):
        contact_parts.append(f'{info.get("location")}')
    if info.get("linkedin"):
        link = info.get("linkedin")
        url = link if link.startswith("http") else f"https://{link}"
        contact_parts.append(f'<a href="{url}"><font color="{heading_color.hexval()}">LinkedIn</font></a>')
    if info.get("github"):
        link = info.get("github")
        url = link if link.startswith("http") else f"https://{link}"
        contact_parts.append(f'<a href="{url}"><font color="{heading_color.hexval()}">GitHub</font></a>')

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
            title_str = f"<b>{exp.get('role', '')}</b>"
            if exp.get('company'):
                title_str += f" — {exp.get('company')}"
            story.append(Paragraph(title_str, exp_title_style))
            
            meta_parts = []
            if exp.get('location'):
                meta_parts.append(f"<b>{exp.get('location')}</b>")
            if exp.get('dates'):
                meta_parts.append(f"<b>{exp.get('dates')}</b>")
            if meta_parts:
                story.append(Paragraph(" | ".join(meta_parts), exp_meta_style))

            for b in exp.get("bullets", []):
                story.append(Paragraph(f"• {b}", bullet_style))
            story.append(Spacer(1, 4))

    if parsed.get("projects"):
        story.append(Paragraph("KEY PROJECTS", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        for proj in parsed.get("projects"):
            title_str = f"<b>{proj.get('name', '')}</b>"
            if proj.get('link'):
                link_url = proj.get('link') if proj.get('link').startswith('http') else f"https://{proj.get('link')}"
                title_str += f' &nbsp;—&nbsp; <a href="{link_url}"><font color="{heading_color.hexval()}">{proj.get("link")}</font></a>'
            story.append(Paragraph(title_str, exp_title_style))
            if proj.get('description'):
                story.append(Paragraph(proj.get('description'), body_style))
            for b in proj.get("bullets", []):
                story.append(Paragraph(f"• {b}", bullet_style))
            story.append(Spacer(1, 4))


    if parsed.get("education"):
        story.append(Paragraph("EDUCATION", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        for edu in parsed.get("education"):
            degree_str = f"<b>{edu.get('degree', '')}</b>"
            if edu.get('dates'):
                degree_str += f" &nbsp;<font color='#64748b'>({edu.get('dates')})</font>"
            story.append(Paragraph(degree_str, exp_title_style))

            if edu.get('institution'):
                story.append(Paragraph(f"<i>{edu.get('institution')}</i>", exp_meta_style))
            
            if edu.get('location'):
                story.append(Paragraph(edu.get('location'), body_style))
            story.append(Spacer(1, 4))

    skills_data = parsed.get("skills")
    if skills_data:
        story.append(Paragraph("SKILLS & TECHNICAL EXPERTISE", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=6))
        
        if isinstance(skills_data, list):
            items_str = ", ".join(skills_data)
            story.append(Paragraph(f"<b>Technical Skills:</b> {items_str}", body_style))
            story.append(Spacer(1, 3))
        elif isinstance(skills_data, dict):
            for cat_name, items in skills_data.items():
                if not items:
                    continue
                if isinstance(items, list):
                    items_str = ", ".join(items)
                else:
                    items_str = str(items)
                
                cat_p = f"<b>{cat_name}:</b> {items_str}"
                story.append(Paragraph(cat_p, body_style))
                story.append(Spacer(1, 3))
        else:
            story.append(Paragraph(str(skills_data), body_style))
            story.append(Spacer(1, 3))


    doc.build(story)
    buffer.seek(0)
    return buffer


@resume.route('/export-custom-pdf', methods=['POST'])
def export_custom_pdf():
    """Generates and downloads a styled PDF from raw JSON parsed_data and template options."""
    data = request.get_json() or {}
    parsed = data.get("parsed_data", {})
    template_id = data.get("template_id", "modern-tech")
    accent_hex = data.get("accent_color", "#2563eb")
    filename = data.get("filename", "SkillSync_Resume.pdf")

    if not parsed:
        return jsonify({"success": False, "error": "Missing parsed_data"}), 400

    try:
        buffer = build_template_pdf_story(parsed, template_id, accent_hex)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename if filename.endswith(".pdf") else f"{filename}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500




@resume.route('/<int:resume_id>/export/pdf', methods=['GET'])
@login_required
def export_pdf(resume_id):
    user_id = session.get('user_id')
    res = Resume.query.filter_by(id=resume_id, user_id=user_id).first_or_404()
    parsed = res.get_parsed_data()
    
    template_id = request.args.get('template', 'modern-tech')
    accent_hex = request.args.get('accent', '#1e40af')

    buffer = build_template_pdf_story(parsed, template_id, accent_hex)
    
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


