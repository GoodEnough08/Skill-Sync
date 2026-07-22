import re

class SkillManager:
    def __init__(self):
        self.skill_taxonomy = {
            "Languages": [
                "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Golang", "Rust", "Ruby",
                "PHP", "Swift", "Kotlin", "R", "Scala", "SQL", "HTML5", "CSS3", "Bash", "Shell", "PowerShell"
            ],
            "Frameworks & Libraries": [
                "React", "React Native", "Next.js", "Vue.js", "Angular", "Node.js", "Express.js", "Django",
                "Flask", "FastAPI", "Spring Boot", "ASP.NET", "Laravel", "Tailwind CSS", "Bootstrap", "jQuery",
                "PyTorch", "TensorFlow", "Keras", "Scikit-Learn", "Pandas", "NumPy", "OpenCV"
            ],
            "Cloud & DevOps": [
                "AWS", "Amazon Web Services", "Azure", "Google Cloud", "GCP", "Docker", "Kubernetes", "K8s",
                "Terraform", "Ansible", "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "Linux", "Nginx"
            ],
            "Databases & Analytics": [
                "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite", "DynamoDB", "Cassandra",
                "Snowflake", "BigQuery", "Apache Kafka", "Spark", "Hadoop", "GraphQL", "REST API", "gRPC"
            ],
            "Tools & Methods": [
                "Git", "GitHub", "GitLab", "Jira", "Confluence", "Postman", "Figma", "Docker Desktop",
                "Agile", "Scrum", "CI/CD Pipelines", "TDD", "Microservices", "System Design", "Unit Testing"
            ],
            "Soft Skills": [
                "Leadership", "Communication", "Problem Solving", "Teamwork", "Project Management",
                "Critical Thinking", "Time Management", "Adaptability", "Collaboration", "Mentorship"
            ]
        }
        
        # Build flattened normalized dictionary for fast matching
        self.flat_skills = {}
        for cat, skills in self.skill_taxonomy.items():
            for sk in skills:
                self.flat_skills[sk.lower()] = (sk, cat)

    def extract_skills_from_text(self, text):
        """Extract taxonomy skills found in raw text."""
        found_skills = {}
        text_lower = text.lower()

        for norm_skill, (canonical_name, category) in self.flat_skills.items():
            # Use word boundary search for exact matching
            pattern = r'\b' + re.escape(norm_skill) + r'\b'
            if re.search(pattern, text_lower):
                if category not in found_skills:
                    found_skills[category] = []
                if canonical_name not in found_skills[category]:
                    found_skills[category].append(canonical_name)

        return found_skills

    def flatten_skills(self, categorized_skills):
        """Flatten categorized dictionary into a single list of skill strings."""
        flat = []
        for cat, skills in categorized_skills.items():
            flat.extend(skills)
        return list(dict.fromkeys(flat))

    def analyze_skill_gap(self, resume_text, job_description_text):
        """Compare resume text against job description to identify matched vs missing skills."""
        resume_skills_dict = self.extract_skills_from_text(resume_text)
        jd_skills_dict = self.extract_skills_from_text(job_description_text)

        resume_skills_set = set([s.lower() for s in self.flatten_skills(resume_skills_dict)])
        
        matched_skills = []
        missing_skills = []

        for cat, skills in jd_skills_dict.items():
            for sk in skills:
                if sk.lower() in resume_skills_set:
                    matched_skills.append({"skill": sk, "category": cat})
                else:
                    missing_skills.append({"skill": sk, "category": cat})

        return {
            "resume_skills": resume_skills_dict,
            "jd_skills": jd_skills_dict,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "match_count": len(matched_skills),
            "missing_count": len(missing_skills)
        }
