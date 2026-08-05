from flask import Blueprint, render_template, session, redirect, url_for
from models.user import Resume, User
from routes.auth import login_required, get_current_user
from ai.ats import ATSAnalyzer

main = Blueprint('main', __name__)
ats_analyzer = ATSAnalyzer()

REFERENCE_RESUME_DATA = {
    "contact_info": {
        "name": "Alex Morgan",
        "email": "alex.morgan@example.com",
        "phone": "+1 (555) 234-5678",
        "location": "San Francisco, CA",
        "linkedin": "linkedin.com/in/alexmorgan-tech",
        "github": "github.com/alexmorgan-dev"
    },
    "summary": "Results-driven Staff Systems & AI Engineer with 8+ years of experience architecting distributed microservices, cloud infrastructure, and enterprise AI models. Proven track record of scaling high-throughput APIs serving 10M+ daily requests and leading high-performing engineering teams.",
    "experience": [
        {
            "role": "Staff Software & AI Engineer",
            "company": "Nexus Technologies",
            "dates": "2022 - Present",
            "bullets": [
                "Architected and deployed a distributed Python & FastAPI microservices infrastructure, reducing API latency by 42% across 10M+ daily active users.",
                "Spearheaded the integration of PyTorch LLM inference pipelines on AWS EKS, accelerating request throughput by 3.5x while lowering cloud compute costs by $120,000 annually.",
                "Engineered automated CI/CD deployment workflows with Docker, Kubernetes, and Terraform, achieving 99.99% system uptime and zero-downtime releases."
            ]
        },
        {
            "role": "Senior Full Stack Engineer",
            "company": "CloudScale Solutions",
            "dates": "2019 - 2022",
            "bullets": [
                "Led a cross-functional team of 6 engineers to build a real-time analytics dashboard using React, TypeScript, and WebSockets, increasing customer retention by 28%.",
                "Optimized PostgreSQL database query execution plans and Redis caching layer, decreasing database load by 55% during peak traffic hours."
            ]
        }
    ],
    "education": [
        {
            "degree": "M.S. in Computer Science & Artificial Intelligence",
            "institution": "Stanford University",
            "dates": "2017 - 2019"
        },
        {
            "degree": "B.S. in Software Engineering",
            "institution": "University of California, Berkeley",
            "dates": "2013 - 2017"
        }
    ],
    "skills": [
        "Python", "TypeScript", "React", "FastAPI", "PyTorch", "Docker", "Kubernetes", "AWS", "PostgreSQL", "Redis", "Terraform", "GraphQL", "CI/CD", "System Design", "Microservices"
    ]
}

@main.route('/')
def index():
    user = get_current_user()
    recent_resumes = []
    if user:
        recent_resumes = Resume.query.filter_by(user_id=user.id).order_by(Resume.created_at.desc()).limit(6).all()
    return render_template('index.html', recent_resumes=recent_resumes, user=user)

@main.route('/demo')
def demo_page():
    """Public 90+ ATS score reference resume showcase available without login."""
    sample_jd = """
    We are seeking a Senior / Staff Software Engineer to build high-scale microservices, cloud infrastructure, and AI systems. Requirements: Python, FastAPI, React, Docker, Kubernetes, AWS, PostgreSQL, Redis, CI/CD, and strong architectural experience.
    """
    analysis = ats_analyzer.analyze(REFERENCE_RESUME_DATA, sample_jd)
    return render_template('demo.html', resume_data=REFERENCE_RESUME_DATA, analysis=analysis)

@main.route('/analyze')
@login_required
def analyze_page():
    user = get_current_user()
    return render_template('analyze.html', user=user)

@main.route('/editor/<int:resume_id>')
@login_required
def editor_page(resume_id):
    user = get_current_user()
    resume = Resume.query.filter_by(id=resume_id, user_id=user.id).first_or_404()
    return render_template('editor.html', resume=resume, user=user)

@main.route('/builder')
def builder_page():
    user = get_current_user()
    return render_template('builder.html', user=user)

