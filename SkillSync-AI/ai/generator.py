import re
import json
import random
from ai.skills import SkillManager

class PromptResumeGenerator:
    def __init__(self):
        self.skill_manager = SkillManager()

    def generate_from_prompt(self, prompt, target_role="", exp_level="Mid-Level", job_description=""):
        """
        Generates a rich, structured JSON resume object based on a user prompt,
        target role, experience level, and optional job description.
        """
        prompt_clean = prompt.strip() if prompt else ""
        
        # 1. Infer Target Role if not explicitly provided
        if not target_role:
            target_role = self._infer_role(prompt_clean, job_description)

        # 2. Extract or infer contact information
        contact_info = self._extract_contact_info(prompt_clean, target_role)

        # 3. Extract or infer skills
        extracted_skills = self._extract_and_enrich_skills(prompt_clean, target_role, job_description)

        # 4. Generate Work Experiences with metric-driven bullets
        experiences = self._generate_experiences(prompt_clean, target_role, exp_level, extracted_skills, job_description)

        # 5. Generate Education
        education = self._generate_education(prompt_clean, exp_level)

        # 6. Generate Projects (if applicable)
        projects = self._generate_projects(prompt_clean, target_role, extracted_skills)

        # 7. Generate Executive Summary
        summary = self._generate_executive_summary(prompt_clean, target_role, exp_level, extracted_skills, job_description)

        parsed_resume = {
            "contact_info": contact_info,
            "summary": summary,
            "experience": experiences,
            "education": education,
            "projects": projects,
            "skills": extracted_skills,
            "raw_text": f"{contact_info['name']} {summary} {' '.join([e['role'] + ' ' + ' '.join(e['bullets']) for e in experiences])}"
        }

        return parsed_resume

    def _infer_role(self, prompt, job_description):
        text = f"{prompt} {job_description}".lower()
        if "frontend" in text or "react" in text or "vue" in text or "ui/ux" in text:
            return "Senior Frontend Engineer"
        elif "backend" in text or "python" in text or "java" in text or "go" in text or "node" in text:
            return "Senior Backend Engineer"
        elif "full stack" in text or "fullstack" in text or "web developer" in text:
            return "Lead Full Stack Engineer"
        elif "data scientist" in text or "machine learning" in text or "ai" in text or "deep learning" in text:
            return "AI / Data Science Specialist"
        elif "data analyst" in text or "analytics" in text or "sql" in text or "bi" in text:
            return "Data & Business Intelligence Analyst"
        elif "devops" in text or "cloud" in text or "kubernetes" in text or "sre" in text or "aws" in text:
            return "Cloud & DevOps Systems Engineer"
        elif "product manager" in text or "pm" in text or "agile" in text or "scrum" in text:
            return "Technical Product Manager"
        elif "mobile" in text or "flutter" in text or "react native" in text or "ios" in text or "android" in text:
            return "Mobile Application Engineer"
        elif "cybersecurity" in text or "security" in text or "penetration" in text:
            return "Cybersecurity Systems Specialist"
        elif "marketing" in text or "seo" in text or "content" in text:
            return "Digital Marketing & Growth Specialist"
        elif "finance" in text or "accountant" in text or "financial" in text:
            return "Financial & Risk Analyst"
        else:
            return "Software & Systems Engineer"

    def _extract_contact_info(self, prompt, target_role):
        # Name extraction heuristic
        name_match = re.search(r"(?:my name is|i am|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", prompt, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).title()
        else:
            name = "Jordan Lee"

        # Email extraction
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", prompt)
        email = email_match.group(0) if email_match else f"{name.lower().replace(' ', '.')}@example.com"

        # Phone extraction
        phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", prompt)
        phone = phone_match.group(0) if phone_match else "+1 (555) 382-9102"

        # Location extraction
        loc_match = re.search(r"(?:living in|based in|located in|from)\s+([A-Z][a-zA-Z\s,]+)", prompt)
        non_locations = {"Python", "Java", "React", "Docker", "Kubernetes", "AWS", "SQL", "JavaScript", "TypeScript"}
        if loc_match:
            loc_candidate = loc_match.group(1).strip()
            # Trim trailing filler words
            loc_candidate = re.split(r'\b(with|having|and|where|in|for)\b', loc_candidate, flags=re.IGNORECASE)[0].strip()
            if loc_candidate and loc_candidate not in non_locations and len(loc_candidate) < 30:
                location = loc_candidate
            else:
                location = "San Francisco, CA"
        else:
            location = "San Francisco, CA"



        handle = name.lower().replace(' ', '')
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "linkedin": f"linkedin.com/in/{handle}",
            "github": f"github.com/{handle}"
        }

    def _extract_and_enrich_skills(self, prompt, target_role, job_description):
        # Extract skills present in prompt & JD
        combined_text = f"{prompt} {job_description}"
        extracted = self.skill_manager.extract_skills_from_text(combined_text)
        flat_extracted = self.skill_manager.flatten_skills(extracted)

        role_lower = target_role.lower()
        default_skills = []
        if "frontend" in role_lower:
            default_skills = ["React", "TypeScript", "JavaScript", "HTML5/CSS3", "Next.js", "Redux", "Tailwind CSS", "REST APIs", "Jest", "Git"]
        elif "backend" in role_lower:
            default_skills = ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes", "AWS", "GraphQL", "CI/CD", "Microservices"]
        elif "data" in role_lower or "ai" in role_lower:
            default_skills = ["Python", "PyTorch", "TensorFlow", "SQL", "Pandas", "Scikit-Learn", "AWS SageMaker", "Docker", "ETL Pipelines", "Tableau"]
        elif "devops" in role_lower:
            default_skills = ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD", "Prometheus", "Grafana", "Linux", "Python", "Ansible"]
        elif "product" in role_lower:
            default_skills = ["Product Strategy", "Agile/Scrum", "Jira", "User Research", "A/B Testing", "SQL", "Wireframing", "Roadmapping"]
        else:
            default_skills = ["Python", "JavaScript", "React", "Node.js", "Docker", "PostgreSQL", "AWS", "Git", "REST APIs", "System Design"]

        # Merge extracted with default skills ensuring no duplicates
        all_skills = list(dict.fromkeys(flat_extracted + default_skills))
        return all_skills[:14]

    def _generate_experiences(self, prompt, target_role, exp_level, skills, job_description):
        # Determine number of companies based on exp_level
        if exp_level.lower() in ["senior", "lead / executive", "lead"]:
            num_exp = 3
        elif exp_level.lower() == "entry":
            num_exp = 1
        else:
            num_exp = 2

        role_parts = target_role.split(" ")
        core_title = role_parts[-1] if len(role_parts) > 1 else target_role

        companies = [
            {"name": "Apex Innovations", "dates": "2023 - Present", "loc": "San Francisco, CA"},
            {"name": "Nexus Systems Inc.", "dates": "2021 - 2023", "loc": "Austin, TX"},
            {"name": "Vanguard Tech Solutions", "dates": "2019 - 2021", "loc": "Boston, MA"}
        ]

        experiences = []
        for i in range(num_exp):
            c = companies[i]
            if i == 0:
                title = target_role
            elif i == 1:
                title = f"Mid-Level {core_title}" if "Senior" in target_role or "Lead" in target_role else target_role
            else:
                title = f"Associate {core_title}"

            bullets = self._create_bullets(title, c["name"], i, prompt, skills, job_description)

            experiences.append({
                "role": title,
                "company": c["name"],
                "dates": c["dates"],
                "location": c["loc"],
                "bullets": bullets
            })

        return experiences

    def _create_bullets(self, title, company, index, prompt, skills, job_description):
        # Pick 2 relevant skills for bullets
        s1 = skills[0] if len(skills) > 0 else "modern tech stacks"
        s2 = skills[1] if len(skills) > 1 else "cloud infrastructure"
        s3 = skills[2] if len(skills) > 2 else "database architecture"
        s4 = skills[3] if len(skills) > 3 else "CI/CD automation"

        if index == 0:
            bullets = [
                f"Architected and deployed high-performance scalable systems utilizing {s1} and {s2}, reducing overall request latency by 42% across 2M+ active monthly users.",
                f"Spearheaded cross-functional team initiatives to modernize microservices infrastructure with {s3}, increasing deployment reliability to 99.99% uptime.",
                f"Optimized data query execution plans and caching mechanisms, slashing cloud operational compute overhead by $85,000 annually.",
                f"Mentored 4 junior engineers, established rigorous automated testing standards, and elevated codebase test coverage to 94%."
            ]
        elif index == 1:
            bullets = [
                f"Developed end-to-end features and APIs integrating {s1} and {s4}, driving a 30% increase in product adoption and customer satisfaction.",
                f"Refactored legacy application codebase to modern modular standards, decreasing error rate by 48% and streamlining developer onboarding.",
                f"Collaborated with product designers and security teams to implement robust OAuth2 authentication and WCAG accessibility compliance."
            ]
        else:
            bullets = [
                f"Engineered key modules for core SaaS application at {company} using {s2}, accelerating feature release cycles by 25%.",
                f"Automated unit testing and CI/CD pipelines, saving the engineering team 12+ hours of manual deployment work per week.",
                f"Authored comprehensive technical documentation and API specifications for internal and client-facing endpoints."
            ]

        # Inject details from user prompt if matched (only for top position)
        if index == 0 and prompt:
            prompt_lower = prompt.lower()
            if "reduced" in prompt_lower or "increased" in prompt_lower or "%" in prompt_lower:
                # Find metric sentence in prompt
                sentences = [s.strip() for s in re.split(r'[.!?]', prompt) if len(s.strip()) > 15]
                for s in sentences:
                    if any(kw in s.lower() for kw in ["built", "developed", "led", "managed", "reduced", "increased", "created", "architected"]):
                        bullets[0] = f"{s[0].upper()}{s[1:]}."
                        break

        return bullets


    def _generate_education(self, prompt, exp_level):
        degree = "B.S. in Computer Science & Software Engineering"
        institution = "University of California, Berkeley"
        dates = "2016 - 2020"

        if "master" in prompt.lower() or "m.s." in prompt.lower() or "mit" in prompt.lower() or "stanford" in prompt.lower():
            degree = "M.S. in Computer Science & Artificial Intelligence"
            institution = "Stanford University"
            dates = "2020 - 2022"

        return [
            {
                "degree": degree,
                "institution": institution,
                "dates": dates,
                "location": "Berkeley, CA"
            }
        ]

    def _generate_projects(self, prompt, target_role, skills):
        s1 = skills[0] if skills else "Python"
        s2 = skills[1] if len(skills) > 1 else "React"
        
        return [
            {
                "name": f"AI-Powered {target_role.split()[-1]} Analytics Engine",
                "description": f"Designed an open-source real-time intelligence platform built with {s1}, {s2}, and Redis. Received 1,200+ GitHub stars.",
                "bullets": [
                    f"Implemented distributed event streaming handling 50k events/sec.",
                    f"Deployed containerized application via Docker & Kubernetes on AWS."
                ]
            }
        ]

    def _generate_executive_summary(self, prompt, target_role, exp_level, skills, job_description):
        skills_str = ", ".join(skills[:5]) if skills else "modern frameworks and cloud platforms"
        
        years = "5+"
        if exp_level.lower() == "senior":
            years = "7+"
        elif exp_level.lower() == "lead / executive":
            years = "10+"
        elif exp_level.lower() == "entry":
            years = "1-2"

        summary = f"Results-driven {target_role} with {years} years of proven expertise in architecting high-impact applications and scaling distributed systems. Highly proficient in {skills_str}, with a strong track record of optimizing system performance, reducing latency, and delivering business value."

        if job_description:
            summary += " ADEPT AT ALIGNING TECHNICAL EXCELLENCE WITH TARGET ATS REQUIREMENTS FOR MAXIMUM IMPACT."

        return summary
