# SkillSync AI - Comprehensive Project Architecture & Technical Documentation

---

## 📌 Executive Summary

**SkillSync AI** is a next-generation AI-powered Resume Builder, Multi-User ATS (Applicant Tracking System) Analyzer, and Skill Gap Optimization Platform. The application enables users to upload existing resumes, parse structured data, analyze ATS compliance scores, align bullet points with job descriptions, and generate high-scoring tailored resumes from simple text prompts.

---

## 🛠️ Technology Stack & System Architecture

```
+-----------------------------------------------------------------------+
|                            FRONTEND LAYER                             |
|  - HTML5 (Jinja2 Templates)    - Vanilla CSS (Glassmorphism System)   |
|  - JavaScript (ES6 Modules)    - FontAwesome 6 & Google Fonts         |
|  - Chart.js (ATS Gauges)       - HTML2PDF / Styled Print Renderer     |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                            BACKEND LAYER                              |
|  - Python 3.11                 - Flask Web Framework                  |
|  - SQLAlchemy ORM              - SQLite Database Engine               |
|  - Gunicorn WSGI Server        - Werkzeug Password Hashing            |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                        AI & NLP PARSING ENGINE                        |
|  - PyPDF2 / docx Text Extractor - Regex Pattern Matcher               |
|  - Categorized Skill Engine    - Prompt-Driven Resume Builder         |
|  - ATS Scoring & Gap Matcher   - Metric & Action Verb Enhancer        |
+-----------------------------------------------------------------------+
```

---

## 📂 Complete File-by-File Breakdown

### 📁 Root Directory (`/`)

* **`Procfile`**: Specifies the Gunicorn WSGI server entrypoint (`web: gunicorn --chdir SkillSync-AI app:app`) for cloud deployment platforms like Render or Heroku.
* **`render.yaml`**: Infrastructure-as-code configuration blueprint for Render deployment, defining environment variables, Python version, build commands, and start commands.
* **`requirements.txt`**: Top-level Python dependency manifest.
* **`README.md`**: Project title and repository entry reference.
* **`PROJECT_DOCUMENTATION.md`**: Master architectural documentation explaining every file, feature, and implementation step.

---

### 📁 `SkillSync-AI/` (Application Core)

* **`app.py`**: The primary Flask application factory. Configures secret keys, database URIs (`sqlite:///skillsync.db`), upload size limits (16 MB), registers blueprints (`main`, `auth`, `resume`, `profile`), and creates database tables on startup.
* **`database.py`**: Instantiates the central SQLAlchemy ORM object (`db = SQLAlchemy()`) to prevent circular imports across routes and models.
* **`Procfile` & `requirements.txt`**: Local build definitions for subdirectory deployment environments.

---

### 📁 `SkillSync-AI/ai/` (AI & NLP Intelligence Engine)

* **`parser.py`**:
  * Extracts text from uploaded files (`PDF`, `DOCX`, `TXT`).
  * Uses regex heuristics and NLP parsing to structure raw text into structured JSON: contact details (name, email, phone, location, LinkedIn, GitHub), professional summary, work experience items, education degrees, skills, and projects.
* **`ats.py`**:
  * Implements the **ATS Optimization Algorithm**.
  * Calculates sub-scores:
    * **Structure Score (25%)**: Checks contact completeness, standard headers, section presence.
    * **Action Verbs Density (25%)**: Evaluates power action verbs at the start of bullet points.
    * **Impact & Metrics Score (25%)**: Detects numbers, percentages, dollar values, and metrics.
    * **Keyword Relevance Score (25%)**: Matches extracted skills against job description text.
  * Generates missing skill tags, matched skill tags, and actionable improvement feedback.
* **`generator.py`**:
  * Prompt-driven AI resume generation core.
  * Takes target job role, experience level, user bio/prompt, and optional target job description to synthesize complete, highly formatted resume objects.
* **`skills.py`**:
  * Contains master dictionaries of **Categorized Technical & Soft Skills** (Frontend, Backend, Cloud/DevOps, AI/Data, Databases, Testing, Tools).
  * Contains a dictionary of **Strong Action Verbs** (e.g., *Engineered, Architected, Spearheaded, Optimized, Quantified*).

---

### 📁 `SkillSync-AI/models/` (Database Data Models)

* **`user.py`**: Defines the SQLAlchemy database schema:
  * **`User`**: Manages user accounts (`id`, `username`, `email`, `password_hash`, `created_at`). Uses Werkzeug hash functions (`set_password`, `check_password`).
  * **`Resume`**: Stores resumes (`id`, `user_id`, `title`, `original_filename`, `file_type`, `parsed_data` as JSON string, `full_text`, `created_at`, `updated_at`).
  * **`Analysis`**: Stores ATS scoring history (`id`, `resume_id`, `job_title`, `ats_score`, `structure_score`, `keyword_score`, `impact_score`, `verb_score`, `missing_skills`, `matched_skills`, `feedback`).
* **`db.py`**: Exposes database reference utilities.

---

### 📁 `SkillSync-AI/routes/` (Flask Controllers & Blueprints)

* **`main.py`**: Handles primary web pages:
  * `/`: Home dashboard displaying upload dropzone, recent resumes, and feature cards.
  * `/builder`: Prompt-driven AI resume maker step-by-step page.
  * `/demo`: Public 90+ ATS Score reference demo (accessible without login).
  * `/analyze`: ATS analysis dashboard page.
* **`auth.py`**: Handles authentication:
  * `/login` (GET/POST): Authenticates user sessions.
  * `/register` (GET/POST): Registers new accounts with password hashing.
  * `/logout`: Clears user session.
* **`resume.py`**: API & Resume Workspace management:
  * `/editor/<id>`: Renders dual-pane interactive editor for saved resumes.
  * `/api/resume/parse` (POST): Accepts file uploads and parses text.
  * `/api/resume/generate` (POST): Generates AI resumes from prompt inputs.
  * `/api/resume/save` (POST): Persists edited resumes to database.
  * `/api/resume/<id>/delete` (POST): Deletes a resume from user history.
  * `/api/resume/export-pdf` (POST): Serves styled HTML for client-side PDF export.
* **`profile.py`**: User profile management routes.

---

### 📁 `SkillSync-AI/templates/` (Jinja2 Views & UI Templates)

* **`base.html`**: Master HTML shell. Includes Google Fonts (Outfit & Inter), FontAwesome 6 icons, Chart.js, CSS stylesheets, main JS scripts, flash messages, toast notification overlay, and the **responsive mobile navigation bar drawer**.
* **`index.html`**: Home landing view featuring hero banner, file upload dropzone, job description input, recent resumes grid, and feature highlights.
* **`builder.html`**: Step-by-step AI Resume Builder:
  * Step 1: Template Gallery (5 interactive cards with accent color dot pickers).
  * Step 2: Role selection, quick preset buttons, prompt text box, and job description drawer.
  * Step 3: Live split-screen workspace with ATS score circle and quick content edit tabs.
* **`editor.html`**: Split-screen resume editor with structured section inputs, personal info form grid, and live paper sheet preview.
* **`demo.html`**: Public reference demo displaying 95-score gold standard resume, Chart.js ATS score gauge, and breakdown progress bars.
* **`analyze.html`**: Standalone upload and analysis interface.
* **`login.html` & `register.html`**: Dark glassmorphic user authentication cards with form validation.

---

### 📁 `SkillSync-AI/static/` (Frontend Static Assets)

* **`static/css/style.css`**:
  * **Design System**: Defines CSS root variables for colors, dark mode gradients, border glows, radii, and typography.
  * **Components**: Buttons (`.btn-primary`, `.btn-secondary`, `.btn-ai`), Glass cards (`.glass-card`), Dropzones, Tags, Feedback items.
  * **5 Resume Templates**:
    1. `modern-tech`: Dark tech headers, cyan/blue accents, pill tags.
    2. `executive-elite`: Serif typography, gold/amber dividers, centered headers.
    3. `minimalist-clean`: Clean layout, emerald accents, subtle borders.
    4. `creative-prof`: Modern gradient header banner, violet accents.
    5. `ats-formal`: Corporate single-column format, high ATS compatibility.
  * **Comprehensive Responsive Media Queries**: Handles tablet (`max-width: 992px`), mobile (`max-width: 768px`), and small mobile (`max-width: 480px`) layout adaptations.
* **`static/js/main.js`**:
  * **`initMobileNav()`**: Toggles mobile hamburger menu drawer, handles backdrop overlays, closes on navigation clicks, and prevents background page scrolling.
  * **`initFileUpload()`**: Drag-and-drop file upload handling via AJAX.
  * **`initEditor()`**: Live split-screen paper sheet rendering, real-time input syncing, template theme switching, color dot selection, and PDF export.
  * **`initJdMatcher()`**: Job description keyword alignment.
  * **Toast Notifications**: Interactive toast alert container (`showToast()`).

---

## 🚀 What We Have Done & How We Implemented It

### 1. Mobile Responsiveness & Mobile Navbar Drawer
* **Problem**: The original navigation bar links wrapped awkwardly on mobile screens, and multi-column grid layouts in the workspace and editor caused horizontal scrollbars on mobile phones.
* **Solution**:
  1. Built a **Mobile Drawer Navigation Bar** in `base.html` with a hamburger button (`#nav-toggle`) and backdrop overlay (`#nav-backdrop`).
  2. Created `initMobileNav()` in `main.js` to animate the mobile drawer (`transform: translateY(0)`), toggle icon states (`fa-bars` / `fa-xmark`), lock body scroll, and automatically close when links are tapped.
  3. Replaced static inline grid columns with CSS classes (`.workspace-grid`, `.form-grid-2`, `.demo-grid-responsive`) in `style.css`.
  4. Added media queries `@media (max-width: 992px)` and `@media (max-width: 768px)` so split-screen workspaces, template galleries, and form fields automatically stack into clean single columns on mobile devices.
  5. Enforced `font-size: 16px` on form inputs for mobile viewports to prevent iOS automatic page zoom on focus.

### 2. Live Multi-Template Gallery & Custom Accent Color Picker
* Integrated 5 customizable resume template design themes into the AI builder and editor.
* Added live color dot pickers allowing users to select accent colors (Royal Blue, Cyber Cyan, Emerald Green, Purple Violet, Warm Amber, Crimson Red) that immediately recalculate template variables in real-time.

### 3. Git Author Configuration & Contribution Graph Fix
* **Problem**: Pushed commits were not producing green contribution squares on GitHub due to a typo in the local Git configuration email (`deepak1a3t2@gmail.com`).
* **Solution**: Updated local and global Git configuration to `deepak1a3t@gmail.com`, amended the commit author, and force-pushed to GitHub to ensure full contribution graph attribution.

---

## 🛠️ How to Run the Project Locally

```bash
# 1. Change directory to SkillSync-AI
cd SkillSync-AI

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run the Flask application
python3 app.py
```

Open your browser at **`http://127.0.0.1:5000`** to access SkillSync AI.
