import os
import re
import fitz  # PyMuPDF
import docx
from ai.skills import SkillManager

class ResumeParser:
    def __init__(self):
        self.skill_manager = SkillManager()
        self.email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.phone_regex = re.compile(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}')
        self.linkedin_regex = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?', re.IGNORECASE)
        self.github_regex = re.compile(r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?', re.IGNORECASE)
        
        self.section_headers = {
            "summary": ["summary", "profile", "about me", "objective", "professional summary", "executive summary"],
            "experience": ["experience", "work experience", "employment history", "professional experience", "work history", "employment"],
            "education": ["education", "academic background", "qualifications", "education & certifications", "academic qualification"],
            "skills": ["skills", "technical skills", "skills & tools", "core competencies", "technologies", "expertise"],
            "projects": ["projects", "personal projects", "academic projects", "key projects"],
            "certifications": ["certifications", "licenses", "certificates", "awards & certifications", "awards"]
        }

    def extract_text(self, file_path):
        """Extract plain text from PDF, DOCX, or TXT file."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self._extract_pdf_text(file_path)
        elif ext in ['.docx', '.doc']:
            return self._extract_docx_text(file_path)
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _extract_pdf_text(self, file_path):
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
        return text

    def _extract_docx_text(self, file_path):
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_data:
                    full_text.append(" | ".join(row_data))
        return "\n".join(full_text)

    def parse(self, text):
        """Parse raw text into structured resume fields."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        contact_info = self._extract_contact_info(text, lines)
        sections = self._segment_sections(lines)
        
        summary = self._parse_summary(sections.get("summary", []))
        experience = self._parse_experience(sections.get("experience", []))
        education = self._parse_education(sections.get("education", []))
        raw_skills = self._parse_skills(sections.get("skills", []), text)
        projects = self._parse_projects(sections.get("projects", []))
        certifications = self._parse_certifications(sections.get("certifications", []))

        return {
            "contact_info": contact_info,
            "summary": summary,
            "experience": experience,
            "education": education,
            "skills": raw_skills,
            "projects": projects,
            "certifications": certifications,
            "raw_text": text
        }

    def _extract_contact_info(self, text, lines):
        email_match = self.email_regex.search(text)
        phone_match = self.phone_regex.search(text)
        linkedin_match = self.linkedin_regex.search(text)
        github_match = self.github_regex.search(text)

        # Candidate name heuristic
        name = "Candidate Name"
        for line in lines[:8]:
            line_clean = re.sub(r'[|•\-\*\:]', '', line).strip()
            if not self.email_regex.search(line) and not self.phone_regex.search(line) and not self.linkedin_regex.search(line) and not self.github_regex.search(line):
                if 2 <= len(line_clean.split()) <= 4 and len(line_clean) < 40:
                    if not any(kw in line_clean.lower() for kw in ["resume", "curriculum", "page", "summary", "experience"]):
                        name = line_clean
                        break

        return {
            "name": name,
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "linkedin": linkedin_match.group(0) if linkedin_match else "",
            "github": github_match.group(0) if github_match else "",
            "location": ""
        }

    def _segment_sections(self, lines):
        sections = {}
        current_section = "summary"
        sections[current_section] = []

        for line in lines:
            line_clean = re.sub(r'[^a-zA-Z\s]', '', line).strip().lower()
            matched_sec = None
            
            for sec_key, headers in self.section_headers.items():
                if line_clean in headers or any(line_clean == h for h in headers):
                    matched_sec = sec_key
                    break
            
            if matched_sec:
                current_section = matched_sec
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections[current_section].append(line)

        return sections

    def _parse_summary(self, summary_lines):
        return " ".join(summary_lines).strip()

    def _parse_experience(self, exp_lines):
        experiences = []
        curr_exp = None

        date_pattern = re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|20\d\d|19\d\d|Present|Current)', re.IGNORECASE)

        for line in exp_lines:
            is_bullet = line.startswith('•') or line.startswith('-') or line.startswith('*') or line.startswith('–') or line.startswith('—') or re.match(r'^\d+[\.\)]', line)
            
            if not is_bullet and (date_pattern.search(line) or len(line) < 65):
                if curr_exp and (curr_exp["role"] or curr_exp["bullets"]):
                    experiences.append(curr_exp)
                
                parts = re.split(r'[|•–—]', line)
                role = parts[0].strip() if len(parts) > 0 else line
                company = parts[1].strip() if len(parts) > 1 else ""
                dates = parts[2].strip() if len(parts) > 2 else ""

                curr_exp = {
                    "role": role,
                    "company": company,
                    "dates": dates,
                    "bullets": []
                }
            else:
                if not curr_exp:
                    curr_exp = {"role": "Professional Experience", "company": "", "dates": "", "bullets": []}
                bullet_clean = re.sub(r'^[•\-\*\–\—\s\d\.\)]+', '', line).strip()
                if bullet_clean:
                    curr_exp["bullets"].append(bullet_clean)

        if curr_exp and (curr_exp["role"] or curr_exp["bullets"]):
            experiences.append(curr_exp)

        return experiences

    def _parse_education(self, edu_lines):
        education_list = []
        curr_edu = None

        degree_keywords = ["bachelor", "master", "phd", "b.s", "m.s", "b.tech", "m.tech", "associate", "degree", "diploma"]

        for line in edu_lines:
            is_degree_line = any(dk in line.lower() for dk in degree_keywords)
            if is_degree_line or len(line) < 65:
                if curr_edu:
                    education_list.append(curr_edu)
                parts = re.split(r'[|•–—]', line)
                degree = parts[0].strip() if len(parts) > 0 else line
                institution = parts[1].strip() if len(parts) > 1 else ""
                dates = parts[2].strip() if len(parts) > 2 else ""
                curr_edu = {"degree": degree, "institution": institution, "dates": dates, "gpa": ""}
            else:
                if curr_edu:
                    curr_edu["institution"] += " " + line

        if curr_edu:
            education_list.append(curr_edu)

        return education_list

    def _parse_skills(self, skill_lines, full_text):
        skills = []
        for line in skill_lines:
            items = re.split(r'[,|•\*\-\:\;\–\—]', line)
            for item in items:
                clean_item = item.strip()
                if clean_item and len(clean_item) < 40 and not any(kw in clean_item.lower() for kw in ["skills", "languages", "frameworks", "tools"]):
                    skills.append(clean_item)

        # Supplement with auto-extracted taxonomy skills from full text if needed
        extracted_taxonomy = self.skill_manager.flatten_skills(self.skill_manager.extract_skills_from_text(full_text))
        for sk in extracted_taxonomy:
            if sk not in skills:
                skills.append(sk)

        return list(dict.fromkeys(skills))

    def _parse_projects(self, proj_lines):
        projects = []
        curr_proj = None

        for line in proj_lines:
            is_bullet = line.startswith('•') or line.startswith('-') or line.startswith('*') or line.startswith('–') or line.startswith('—')
            if not is_bullet and len(line) < 55:
                if curr_proj:
                    projects.append(curr_proj)
                parts = re.split(r'[|•–—]', line)
                name = parts[0].strip()
                tech = parts[1].strip() if len(parts) > 1 else ""
                curr_proj = {"name": name, "technologies": tech, "description": "", "bullets": []}
            else:
                if not curr_proj:
                    curr_proj = {"name": "Project", "technologies": "", "description": "", "bullets": []}
                bullet_clean = re.sub(r'^[•\-\*\–\—\s]+', '', line).strip()
                if bullet_clean:
                    curr_proj["bullets"].append(bullet_clean)

        if curr_proj:
            projects.append(curr_proj)

        return projects

    def _parse_certifications(self, cert_lines):
        certs = []
        for line in cert_lines:
            clean = re.sub(r'^[•\-\*\–\—\s]+', '', line).strip()
            if clean:
                certs.append(clean)
        return certs
