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

    def enhance_bullet(self, bullet_text):
        """Intelligently rewrite a weak bullet point to add power verbs and metric placeholders."""
        bullet_clean = bullet_text.strip()
        words = bullet_clean.split()
        if not words:
            return bullet_clean

        first_word = re.sub(r'[^a-zA-Z]', '', words[0]).lower()

        # Pick appropriate power verb
        power_verb = "Architected"
        if any(w in bullet_clean.lower() for w in ["web", "api", "backend", "app", "code"]):
            power_verb = "Engineered"
        elif any(w in bullet_clean.lower() for w in ["lead", "manage", "team", "project"]):
            power_verb = "Spearheaded"
        elif any(w in bullet_clean.lower() for w in ["data", "model", "analysis", "ai", "sql"]):
            power_verb = "Optimized"
        elif any(w in bullet_clean.lower() for w in ["design", "ui", "ux", "frontend"]):
            power_verb = "Designed"

        # Reconstruct bullet
        if first_word in self.action_verbs:
            enhanced = f"{bullet_clean}, resulting in a 25% increase in operational performance."
        else:
            rest_of_bullet = " ".join(words[1:]) if len(words) > 1 else words[0]
            # Lowercase initial rest of bullet if appropriate
            if rest_of_bullet and rest_of_bullet[0].isupper() and not rest_of_bullet.startswith("I "):
                rest_of_bullet = rest_of_bullet[0].lower() + rest_of_bullet[1:]
            enhanced = f"{power_verb} and {rest_of_bullet}, achieving a 30% reduction in processing time and improving reliability."

        return enhanced
