import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ai.skills import SkillManager

class ATSAnalyzer:
    def __init__(self):
        self.skill_manager = SkillManager()
        self.action_verbs = [
            "architected", "spearheaded", "engineered", "implemented", "optimized",
            "developed", "designed", "accelerated", "automated", "orchestrated",
            "built", "launched", "championed", "led", "enhanced", "delivered",
            "streamlined", "increased", "decreased", "reduced", "scaled", "pioneered",
            "integrated", "refactored", "migrated", "mentored", "established"
        ]

    def analyze(self, parsed_resume, job_description=""):
        """Calculate ATS score, sub-scores, feedback, and skill gap."""
        full_text = parsed_resume.get("raw_text", "")
        if not full_text:
            # Fallback if raw text is not present
            full_text = self._build_full_text_from_parsed(parsed_resume)

        # 1. Structure Score
        structure_score, structure_feedback = self._calc_structure_score(parsed_resume)

        # 2. Impact & Metrics Score
        impact_score, impact_feedback, weak_bullets = self._calc_impact_score(parsed_resume)

        # 3. Action Verb Score
        verb_score, verb_feedback = self._calc_action_verb_score(parsed_resume)

        # 4. Keyword & Relevance Score
        if job_description.strip():
            keyword_score, keyword_feedback = self._calc_keyword_score_with_jd(full_text, job_description)
            skill_gap = self.skill_manager.analyze_skill_gap(full_text, job_description)
        else:
            keyword_score, keyword_feedback = self._calc_keyword_score_generic(full_text)
            skill_gap = {
                "resume_skills": self.skill_manager.extract_skills_from_text(full_text),
                "jd_skills": {},
                "matched_skills": [],
                "missing_skills": [],
                "match_count": 0,
                "missing_count": 0
            }

        # Calculate Overall Composite ATS Score
        total_ats_score = (
            (structure_score * 0.15) +
            (impact_score * 0.25) +
            (verb_score * 0.25) +
            (keyword_score * 0.35)
        )

        overall_feedback = []
        overall_feedback.extend(structure_feedback)
        overall_feedback.extend(impact_feedback)
        overall_feedback.extend(verb_feedback)
        overall_feedback.extend(keyword_feedback)

        return {
            "ats_score": round(total_ats_score, 1),
            "structure_score": round(structure_score, 1),
            "impact_score": round(impact_score, 1),
            "verb_score": round(verb_score, 1),
            "keyword_score": round(keyword_score, 1),
            "feedback": overall_feedback,
            "weak_bullets": weak_bullets,
            "skill_gap": skill_gap
        }

    def _build_full_text_from_parsed(self, parsed):
        parts = []
        info = parsed.get("contact_info", {})
        parts.append(f"{info.get('name', '')} {info.get('email', '')} {info.get('phone', '')}")
        parts.append(parsed.get("summary", ""))
        for exp in parsed.get("experience", []):
            parts.append(f"{exp.get('role', '')} {exp.get('company', '')} {' '.join(exp.get('bullets', []))}")
        for edu in parsed.get("education", []):
            parts.append(f"{edu.get('degree', '')} {edu.get('institution', '')}")
        if isinstance(parsed.get("skills"), list):
            parts.append(" ".join(parsed.get("skills")))
        elif isinstance(parsed.get("skills"), dict):
            parts.append(" ".join(self.skill_manager.flatten_skills(parsed.get("skills"))))
        return "\n".join(parts)

    def _calc_structure_score(self, parsed):
        score = 100.0
        feedback = []

        info = parsed.get("contact_info", {})
        if not info.get("email"):
            score -= 20
            feedback.append({"type": "warning", "section": "Contact Info", "message": "Email address is missing."})
        if not info.get("phone"):
            score -= 15
            feedback.append({"type": "warning", "section": "Contact Info", "message": "Phone number is missing."})
        if not info.get("linkedin"):
            score -= 10
            feedback.append({"type": "info", "section": "Contact Info", "message": "LinkedIn profile link recommended for ATS completeness."})

        if not parsed.get("summary"):
            score -= 15
            feedback.append({"type": "warning", "section": "Summary", "message": "Professional Summary section is missing."})
        
        if not parsed.get("experience"):
            score -= 25
            feedback.append({"type": "warning", "section": "Experience", "message": "Work Experience section is missing."})

        if not parsed.get("education"):
            score -= 15
            feedback.append({"type": "warning", "section": "Education", "message": "Education section is missing."})

        if not parsed.get("skills"):
            score -= 20
            feedback.append({"type": "warning", "section": "Skills", "message": "Skills section is missing."})

        return max(0.0, score), feedback

    def _calc_impact_score(self, parsed):
        all_bullets = []
        for exp in parsed.get("experience", []):
            all_bullets.extend(exp.get("bullets", []))
        for proj in parsed.get("projects", []):
            all_bullets.extend(proj.get("bullets", []))

        if not all_bullets:
            return 50.0, [{"type": "warning", "section": "Impact", "message": "No bullet points found to measure quantitative impact."}], []

        metric_pattern = re.compile(r'(\d+%\b|\$\d+|\d+\+|\b\d+\b)', re.IGNORECASE)
        quantified_bullets = 0
        weak_bullets = []

        for bullet in all_bullets:
            if metric_pattern.search(bullet):
                quantified_bullets += 1
            else:
                weak_bullets.append(bullet)

        quant_ratio = quantified_bullets / len(all_bullets)
        score = quant_ratio * 100.0

        feedback = []
        if quant_ratio < 0.4:
            feedback.append({
                "type": "warning",
                "section": "Impact & Metrics",
                "message": f"Only {int(quant_ratio*100)}% of your bullet points contain quantitative metrics (%, $, numbers). Aim for at least 50%."
            })
        else:
            feedback.append({
                "type": "success",
                "section": "Impact & Metrics",
                "message": f"Great job! {int(quant_ratio*100)}% of your bullet points include clear measurable achievements."
            })

        return min(100.0, max(20.0, score)), feedback, weak_bullets[:5]

    def _calc_action_verb_score(self, parsed):
        all_bullets = []
        for exp in parsed.get("experience", []):
            all_bullets.extend(exp.get("bullets", []))
        for proj in parsed.get("projects", []):
            all_bullets.extend(proj.get("bullets", []))

        if not all_bullets:
            return 50.0, []

        verb_count = 0
        for bullet in all_bullets:
            first_word = bullet.strip().split()[0].lower() if bullet.strip() else ""
            # strip trailing punctuation
            first_word = re.sub(r'[^a-z]', '', first_word)
            if first_word in self.action_verbs:
                verb_count += 1

        verb_ratio = verb_count / len(all_bullets)
        score = min(100.0, max(25.0, verb_ratio * 125.0))

        feedback = []
        if verb_ratio < 0.5:
            feedback.append({
                "type": "warning",
                "section": "Action Verbs",
                "message": "Start more bullet points with strong power verbs (e.g. 'Spearheaded', 'Architected', 'Optimized')."
            })
        else:
            feedback.append({
                "type": "success",
                "section": "Action Verbs",
                "message": "Strong action verb usage across bullet points."
            })

        return score, feedback

    def _calc_keyword_score_with_jd(self, resume_text, job_description):
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf = vectorizer.fit_transform([resume_text, job_description])
            sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            # Convert cosine similarity (0 to 1) to percentage score (scaled appropriately for resumes)
            score = min(100.0, max(30.0, sim * 150.0))
            feedback = [{
                "type": "success" if score > 70 else "warning",
                "section": "Job Match",
                "message": f"Resume matches {int(score)}% of the target job description keywords and context."
            }]
            return score, feedback
        except Exception:
            return 60.0, []

    def _calc_keyword_score_generic(self, resume_text):
        skills_found = self.skill_manager.extract_skills_from_text(resume_text)
        total_skills = len(self.skill_manager.flatten_skills(skills_found))
        if total_skills >= 10:
            score = 90.0
        elif total_skills >= 5:
            score = 75.0
        else:
            score = 55.0

        feedback = [{
            "type": "info",
            "section": "Keywords",
            "message": f"Detected {total_skills} recognized technical and professional skills in your resume."
        }]
        return score, feedback

    def enhance_bullet(self, bullet_text, mode="impact", job_description=""):
        """Intelligently rewrite a bullet point according to selected enhancement mode."""
        bullet_clean = bullet_text.strip()
        if not bullet_clean:
            return bullet_clean

        words = bullet_clean.split()
        first_word = re.sub(r'[^a-zA-Z]', '', words[0]).lower()

        # Determine best action verb
        power_verb = "Architected"
        b_lower = bullet_clean.lower()
        if any(w in b_lower for w in ["web", "api", "backend", "microservice", "service"]):
            power_verb = "Engineered"
        elif any(w in b_lower for w in ["lead", "manage", "team", "project", "product"]):
            power_verb = "Spearheaded"
        elif any(w in b_lower for w in ["data", "model", "analysis", "ai", "sql", "pipeline"]):
            power_verb = "Optimized"
        elif any(w in b_lower for w in ["design", "ui", "ux", "frontend", "interface"]):
            power_verb = "Designed"
        elif any(w in b_lower for w in ["test", "quality", "ci/cd", "automation", "deploy"]):
            power_verb = "Automated"

        # Check if first word is already an action verb
        has_action_verb = first_word in self.action_verbs

        if mode == "keywords" and job_description:
            jd_skills = self.skill_manager.extract_skills_from_text(job_description)
            flat_jd_skills = self.skill_manager.flatten_skills(jd_skills)
            keywords_to_add = [k for k in flat_jd_skills if k.lower() not in b_lower]
            kw_str = f" using {', '.join(keywords_to_add[:2])}" if keywords_to_add else ""
            if has_action_verb:
                enhanced = f"{bullet_clean}{kw_str}, improving cross-functional alignment and technical efficiency."
            else:
                rest = " ".join(words[1:]) if len(words) > 1 else words[0]
                if rest and rest[0].isupper() and not rest.startswith("I "):
                    rest = rest[0].lower() + rest[1:]
                enhanced = f"{power_verb} {rest}{kw_str}, optimizing overall system workflow."
        elif mode == "executive":
            if has_action_verb:
                enhanced = f"{bullet_clean}, driving strategic alignment and enterprise-level execution."
            else:
                rest = " ".join(words[1:]) if len(words) > 1 else words[0]
                if rest and rest[0].isupper() and not rest.startswith("I "):
                    rest = rest[0].lower() + rest[1:]
                enhanced = f"{power_verb} {rest}, establishing scalable architecture and technical standards."
        else: # "impact" mode default
            if has_action_verb:
                enhanced = f"{bullet_clean}, resulting in a 35% boost in operational efficiency and reducing downtime."
            else:
                rest = " ".join(words[1:]) if len(words) > 1 else words[0]
                if rest and rest[0].isupper() and not rest.startswith("I "):
                    rest = rest[0].lower() + rest[1:]
                enhanced = f"{power_verb} and {rest}, delivering a 30% reduction in processing latency and elevating team output."

        return enhanced

    def generate_summary(self, parsed_resume, job_description=""):
        """Generate a tailored, high-impact executive summary for the candidate."""
        info = parsed_resume.get("contact_info", {})
        experiences = parsed_resume.get("experience", [])
        skills = parsed_resume.get("skills", [])
        
        if isinstance(skills, dict):
            skills = self.skill_manager.flatten_skills(skills)

        primary_role = "Software Engineer"
        if experiences and experiences[0].get("role"):
            primary_role = experiences[0].get("role")

        years = min(len(experiences) * 2 + 2, 10)
        skills_str = ", ".join(skills[:5]) if skills else "modern technologies and frameworks"

        summary = f"Results-driven {primary_role} with {years}+ years of experience designing and deploying scalable applications. Proficient in {skills_str}, with a proven track record of optimizing performance and leading high-impact engineering projects."

        if job_description:
            jd_skills = self.skill_manager.extract_skills_from_text(job_description)
            flat_jd = self.skill_manager.flatten_skills(jd_skills)
            if flat_jd:
                summary += f" Highly focused on leveraging {', '.join(flat_jd[:3])} to solve complex technical challenges."

        return summary

    def generate_bullets_for_role(self, role, company="Company", job_description=""):
        """Auto-generate 3 targeted bullet points based on a job title and company."""
        r_lower = (role or "").lower()

        if "frontend" in r_lower or "react" in r_lower or "web" in r_lower:
            bullets = [
                f"Architected responsive single-page web applications at {company} using React, TypeScript, and modern CSS, improving user engagement by 35%.",
                f"Optimized client-side rendering performance and state management, reducing initial page load time by 45%.",
                f"Collaborated with UX design and product teams to implement reusable component libraries and ensure 100% WCAG accessibility compliance."
            ]
        elif "backend" in r_lower or "python" in r_lower or "api" in r_lower or "server" in r_lower:
            bullets = [
                f"Engineered high-throughput RESTful and GraphQL microservices at {company}, handling over 1M+ daily transactions with 99.99% uptime.",
                f"Refactored relational database schema and query execution plans, resulting in a 50% decrease in API endpoint response times.",
                f"Automated CI/CD deployment pipelines using Docker, Kubernetes, and AWS, cutting deployment cycle duration from hours to minutes."
            ]
        elif "full stack" in r_lower or "fullstack" in r_lower or "developer" in r_lower or "engineer" in r_lower:
            bullets = [
                f"Spearheaded end-to-end development of enterprise web features at {company}, integrating React frontends with robust Python/Node.js microservices.",
                f"Architected real-time data streaming pipelines and database models, reducing system latency by 40%.",
                f"Led code reviews, mentored junior developers, and established automated testing protocols that boosted overall code coverage to 92%."
            ]
        elif "data" in r_lower or "ai" in r_lower or "machine learning" in r_lower:
            bullets = [
                f"Developed and deployed production machine learning models at {company}, increasing prediction accuracy by 28%.",
                f"Constructed scalable ETL pipelines for multi-terabyte datasets using Python, SQL, and cloud data warehouses.",
                f"Optimized model inference latency by 3x through quantization and distributed GPU compute cluster management."
            ]
        else:
            bullets = [
                f"Led technical initiatives and project execution at {company}, boosting operational efficiency by 30%.",
                f"Implemented robust software architecture and automated testing workflows, ensuring high system reliability.",
                f"Cross-functionally collaborated with stakeholders to deliver strategic software updates ahead of schedule."
            ]

        return bullets

    def suggest_skills(self, parsed_resume, job_description=""):
        """Suggest top missing ATS skills based on resume text and target job description."""
        full_text = parsed_resume.get("raw_text", "") or self._build_full_text_from_parsed(parsed_resume)
        
        if job_description.strip():
            gap = self.skill_manager.analyze_skill_gap(full_text, job_description)
            missing = [item["skill"] for item in gap.get("missing_skills", [])]
            if missing:
                return missing[:10]

        # Generic recommendation from taxonomy not present in resume
        existing_dict = self.skill_manager.extract_skills_from_text(full_text)
        existing_set = set([s.lower() for s in self.skill_manager.flatten_skills(existing_dict)])
        
        recommended = []
        popular_skills = ["Docker", "Kubernetes", "AWS", "TypeScript", "React", "Python", "CI/CD", "PostgreSQL", "Redis", "Git", "REST API", "System Design"]
        for sk in popular_skills:
            if sk.lower() not in existing_set:
                recommended.append(sk)

        return recommended[:8]

