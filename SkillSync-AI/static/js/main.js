/* ==========================================================================
   SkillSync AI - Frontend Application Logic (Smoothed & Optimized)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initFileUpload();
  initJdMatcher();
  initEditor();
});

/* Utility: Debounce for smooth typing without lag */
function debounce(func, wait = 150) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/* Toast Notification Utility */
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = 'info-circle';
  if (type === 'success') icon = 'check-circle';
  if (type === 'error') icon = 'exclamation-circle';
  if (type === 'warning') icon = 'triangle-exclamation';

  toast.innerHTML = `<i class="fa-solid fa-${icon}"></i> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* File Upload & Drag and Drop */
function initFileUpload() {
  const dropzone = document.getElementById('resume-dropzone');
  const fileInput = document.getElementById('resume-file-input');
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length) {
      fileInput.files = files;
      handleResumeUpload(files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
      handleResumeUpload(fileInput.files[0]);
    }
  });
}

function handleResumeUpload(file) {
  const uploadStatus = document.getElementById('upload-status');
  if (uploadStatus) {
    uploadStatus.innerHTML = `<div style="display:flex;align-items:center;gap:0.75rem;justify-content:center;color:var(--primary);"><i class="fas fa-spinner fa-spin fa-2x"></i> <span>Parsing resume & analyzing ATS score...</span></div>`;
  }

  const formData = new FormData();
  formData.append('file', file);

  const jdInput = document.getElementById('hero-jd-input');
  if (jdInput && jdInput.value.trim()) {
    formData.append('job_description', jdInput.value.trim());
  }

  fetch('/api/resume/upload', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      showToast('Resume uploaded and analyzed successfully!', 'success');
      window.location.href = `/editor/${data.resume_id}`;
    } else {
      showToast(data.error || 'Upload failed', 'error');
      if (uploadStatus) uploadStatus.innerHTML = '';
    }
  })
  .catch(err => {
    console.error(err);
    showToast('An error occurred during upload. Please check file format.', 'error');
    if (uploadStatus) uploadStatus.innerHTML = '';
  });
}

/* Job Description Matcher */
function initJdMatcher() {
  const btn = document.getElementById('analyze-jd-btn');
  if (!btn) return;

  btn.addEventListener('click', () => {
    const resumeId = btn.dataset.resumeId;
    const jdText = document.getElementById('jd-textarea').value;
    const jdTitle = document.getElementById('jd-title-input').value;

    if (!jdText.trim()) {
      showToast('Please paste a target Job Description first.', 'warning');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Analyzing...`;

    fetch(`/api/resume/${resumeId}/analyze-jd`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        job_description: jdText,
        job_title: jdTitle
      })
    })
    .then(res => res.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-magic"></i> Re-Calculate ATS Match Score`;
      if (data.success) {
        showToast('Job Description match completed!', 'success');
        if (data.analysis) {
          updateEditorAtsMeter(data.analysis);
        }
      } else {
        showToast(data.error || 'Match failed', 'error');
      }
    })
    .catch(err => {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-magic"></i> Re-Calculate ATS Match Score`;
      showToast('Error analyzing job description', 'error');
    });
  });
}

/* Interactive Split-Screen Editor */
let currentResumeData = null;
let currentResumeId = null;

function initEditor() {
  const editorContainer = document.getElementById('resume-editor-container');
  if (!editorContainer) return;

  currentResumeId = editorContainer.dataset.resumeId;
  loadResumeData(currentResumeId);

  document.getElementById('save-resume-btn')?.addEventListener('click', saveResumeData);
  document.getElementById('export-pdf-btn')?.addEventListener('click', exportPdf);

  // Template Theme Switcher listener
  document.getElementById('template-select')?.addEventListener('change', (e) => {
    const paper = document.getElementById('paper-preview-sheet');
    if (paper) {
      paper.className = `paper-sheet theme-${e.target.value}`;
    }
  });
}

function loadResumeData(id) {
  fetch(`/api/resume/${id}`)
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        currentResumeData = data.resume.parsed_data || {};
        renderEditorForm(currentResumeData);
        updatePaperPreview(currentResumeData);
        if (data.analysis) {
          updateEditorAtsMeter(data.analysis);
        }
      }
    })
    .catch(err => console.error(err));
}

function renderEditorForm(data) {
  const info = data.contact_info || {};
  setInputValue('edit-name', info.name || '');
  setInputValue('edit-email', info.email || '');
  setInputValue('edit-phone', info.phone || '');
  setInputValue('edit-location', info.location || '');
  setInputValue('edit-linkedin', info.linkedin || '');
  setInputValue('edit-github', info.github || '');
  
  setInputValue('edit-summary', data.summary || '');

  renderExperienceForm(data.experience || []);
  renderEducationForm(data.education || []);
  renderSkillsForm(data.skills || []);

  bindFormInputListeners();
}

function bindFormInputListeners() {
  const debouncedPreviewUpdate = debounce(() => {
    collectFormDataWithoutRebuilding();
    updatePaperPreview(currentResumeData);
  }, 100);

  document.querySelectorAll('#editor-form-wrapper input, #editor-form-wrapper textarea').forEach(input => {
    input.removeEventListener('input', debouncedPreviewUpdate);
    input.addEventListener('input', debouncedPreviewUpdate);
  });
}

function setInputValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function renderExperienceForm(experiences) {
  const container = document.getElementById('experience-list-container');
  if (!container) return;
  container.innerHTML = '';

  experiences.forEach((exp, idx) => {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.padding = '1.25rem';
    card.style.marginBottom = '1rem';

    const bulletsHtml = (exp.bullets || []).map((bullet, bIdx) => `
      <div style="display:flex;gap:0.5rem;margin-bottom:0.5rem;align-items:center;">
        <input type="text" class="form-control exp-bullet-input" data-exp-idx="${idx}" data-bullet-idx="${bIdx}" value="${escapeHtml(bullet)}">
        <button type="button" class="btn btn-ai btn-sm enhance-bullet-btn" data-exp-idx="${idx}" data-bullet-idx="${bIdx}" title="AI Enhance Bullet">
          <i class="fas fa-wand-magic-sparkles"></i> AI Enhance
        </button>
        <button type="button" class="btn btn-secondary btn-sm delete-bullet-btn" data-exp-idx="${idx}" data-bullet-idx="${bIdx}" style="color:#ef4444;">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `).join('');

    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
        <strong style="color:var(--primary);">Position #${idx + 1}</strong>
        <button type="button" class="btn btn-secondary btn-sm delete-exp-btn" data-exp-idx="${idx}" style="color:#ef4444;">
          <i class="fas fa-trash"></i> Remove
        </button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
        <div class="form-group">
          <label class="form-label">Job Title / Role</label>
          <input type="text" class="form-control exp-role-input" data-exp-idx="${idx}" value="${escapeHtml(exp.role || '')}">
        </div>
        <div class="form-group">
          <label class="form-label">Company</label>
          <input type="text" class="form-control exp-company-input" data-exp-idx="${idx}" value="${escapeHtml(exp.company || '')}">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Dates / Duration</label>
        <input type="text" class="form-control exp-dates-input" data-exp-idx="${idx}" value="${escapeHtml(exp.dates || '')}">
      </div>
      <div class="form-group">
        <label class="form-label">Bullet Points & Key Achievements</label>
        <div class="bullets-wrapper-${idx}">
          ${bulletsHtml}
        </div>
        <button type="button" class="btn btn-secondary btn-sm add-bullet-btn" data-exp-idx="${idx}" style="margin-top:0.5rem;">
          <i class="fas fa-plus"></i> Add Bullet Point
        </button>
      </div>
    `;

    container.appendChild(card);
  });

  bindExperienceEvents();
  bindFormInputListeners();
}

function bindExperienceEvents() {
  document.querySelectorAll('.add-exp-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      if (!currentResumeData.experience) currentResumeData.experience = [];
      currentResumeData.experience.push({ role: 'Software Engineer', company: 'Tech Company', dates: '2023 - Present', bullets: ['Engineered backend features using Python and REST APIs.'] });
      renderExperienceForm(currentResumeData.experience);
      updatePaperPreview(currentResumeData);
    };
  });

  document.querySelectorAll('.delete-exp-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      const idx = parseInt(btn.dataset.expIdx);
      currentResumeData.experience.splice(idx, 1);
      renderExperienceForm(currentResumeData.experience);
      updatePaperPreview(currentResumeData);
    };
  });

  document.querySelectorAll('.add-bullet-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      const idx = parseInt(btn.dataset.expIdx);
      currentResumeData.experience[idx].bullets.push('Developed and deployed cloud microservices.');
      renderExperienceForm(currentResumeData.experience);
      updatePaperPreview(currentResumeData);
    };
  });

  document.querySelectorAll('.delete-bullet-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      const eIdx = parseInt(btn.dataset.expIdx);
      const bIdx = parseInt(btn.dataset.bulletIdx);
      currentResumeData.experience[eIdx].bullets.splice(bIdx, 1);
      renderExperienceForm(currentResumeData.experience);
      updatePaperPreview(currentResumeData);
    };
  });

  document.querySelectorAll('.enhance-bullet-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      const eIdx = parseInt(btn.dataset.expIdx);
      const bIdx = parseInt(btn.dataset.bulletIdx);
      const currentBullet = currentResumeData.experience[eIdx].bullets[bIdx];

      if (!currentBullet) return;

      btn.disabled = true;
      btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i>`;

      fetch('/api/resume/enhance-bullet', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ bullet: currentBullet })
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i> AI Enhance`;
        if (data.success && data.enhanced) {
          currentResumeData.experience[eIdx].bullets[bIdx] = data.enhanced;
          renderExperienceForm(currentResumeData.experience);
          updatePaperPreview(currentResumeData);
          showToast('Bullet point enhanced with power verbs and quantitative metrics!', 'success');
        }
      })
      .catch(err => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i> AI Enhance`;
      });
    };
  });
}

function renderEducationForm(education) {
  const container = document.getElementById('education-list-container');
  if (!container) return;
  container.innerHTML = '';

  education.forEach((edu, idx) => {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.padding = '1rem';
    card.style.marginBottom = '0.75rem';

    card.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
        <div class="form-group">
          <label class="form-label">Degree</label>
          <input type="text" class="form-control edu-degree-input" data-edu-idx="${idx}" value="${escapeHtml(edu.degree || '')}">
        </div>
        <div class="form-group">
          <label class="form-label">Institution</label>
          <input type="text" class="form-control edu-inst-input" data-edu-idx="${idx}" value="${escapeHtml(edu.institution || '')}">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Dates / Year</label>
        <input type="text" class="form-control edu-dates-input" data-edu-idx="${idx}" value="${escapeHtml(edu.dates || '')}">
      </div>
    `;

    container.appendChild(card);
  });

  bindFormInputListeners();
}

function renderSkillsForm(skills) {
  const input = document.getElementById('edit-skills');
  if (!input) return;
  if (Array.isArray(skills)) {
    input.value = skills.join(', ');
  } else if (typeof skills === 'object') {
    let all = [];
    Object.values(skills).forEach(arr => all.push(...arr));
    input.value = all.join(', ');
  } else {
    input.value = skills || '';
  }
}

function collectFormDataWithoutRebuilding() {
  if (!currentResumeData) currentResumeData = {};

  currentResumeData.contact_info = {
    name: getInputValue('edit-name'),
    email: getInputValue('edit-email'),
    phone: getInputValue('edit-phone'),
    location: getInputValue('edit-location'),
    linkedin: getInputValue('edit-linkedin'),
    github: getInputValue('edit-github')
  };

  currentResumeData.summary = getInputValue('edit-summary');

  // Collect Experience values directly from DOM inputs
  document.querySelectorAll('.exp-role-input').forEach(input => {
    const idx = parseInt(input.dataset.expIdx);
    if (currentResumeData.experience && currentResumeData.experience[idx]) {
      currentResumeData.experience[idx].role = input.value;
    }
  });
  document.querySelectorAll('.exp-company-input').forEach(input => {
    const idx = parseInt(input.dataset.expIdx);
    if (currentResumeData.experience && currentResumeData.experience[idx]) {
      currentResumeData.experience[idx].company = input.value;
    }
  });
  document.querySelectorAll('.exp-dates-input').forEach(input => {
    const idx = parseInt(input.dataset.expIdx);
    if (currentResumeData.experience && currentResumeData.experience[idx]) {
      currentResumeData.experience[idx].dates = input.value;
    }
  });
  document.querySelectorAll('.exp-bullet-input').forEach(input => {
    const eIdx = parseInt(input.dataset.expIdx);
    const bIdx = parseInt(input.dataset.bulletIdx);
    if (currentResumeData.experience && currentResumeData.experience[eIdx] && currentResumeData.experience[eIdx].bullets[bIdx] !== undefined) {
      currentResumeData.experience[eIdx].bullets[bIdx] = input.value;
    }
  });

  // Collect Education
  document.querySelectorAll('.edu-degree-input').forEach(input => {
    const idx = parseInt(input.dataset.eduIdx);
    if (currentResumeData.education && currentResumeData.education[idx]) {
      currentResumeData.education[idx].degree = input.value;
    }
  });
  document.querySelectorAll('.edu-inst-input').forEach(input => {
    const idx = parseInt(input.dataset.eduIdx);
    if (currentResumeData.education && currentResumeData.education[idx]) {
      currentResumeData.education[idx].institution = input.value;
    }
  });

  // Collect Skills
  const rawSkills = getInputValue('edit-skills');
  currentResumeData.skills = rawSkills.split(',').map(s => s.trim()).filter(s => s);
}

function getInputValue(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

function updatePaperPreview(data) {
  const paper = document.getElementById('paper-preview-sheet');
  if (!paper) return;

  const info = data.contact_info || {};
  const contactParts = [info.email, info.phone, info.location, info.linkedin, info.github].filter(Boolean);

  let html = `
    <h1>${escapeHtml(info.name || 'Candidate Name')}</h1>
    <div class="paper-contact">${escapeHtml(contactParts.join('  •  '))}</div>
  `;

  if (data.summary) {
    html += `
      <h2>Professional Summary</h2>
      <p>${escapeHtml(data.summary)}</p>
    `;
  }

  if (data.experience && data.experience.length) {
    html += `<h2>Work Experience</h2>`;
    data.experience.forEach(exp => {
      html += `
        <div style="margin-bottom:0.85rem;">
          <div style="display:flex;justify-content:space-between;font-weight:600;color:#0f172a;">
            <span>${escapeHtml(exp.role || '')} ${exp.company ? '— ' + escapeHtml(exp.company) : ''}</span>
            <span style="color:#64748b;font-weight:normal;">${escapeHtml(exp.dates || '')}</span>
          </div>
          <ul>
            ${(exp.bullets || []).map(b => `<li>${escapeHtml(b)}</li>`).join('')}
          </ul>
        </div>
      `;
    });
  }

  if (data.education && data.education.length) {
    html += `<h2>Education</h2>`;
    data.education.forEach(edu => {
      html += `
        <div style="display:flex;justify-content:space-between;margin-bottom:0.4rem;">
          <span><strong>${escapeHtml(edu.degree || '')}</strong> ${edu.institution ? '— ' + escapeHtml(edu.institution) : ''}</span>
          <span style="color:#64748b;">${escapeHtml(edu.dates || '')}</span>
        </div>
      `;
    });
  }

  let skillsStr = '';
  if (Array.isArray(data.skills)) {
    skillsStr = data.skills.join(', ');
  } else if (data.skills) {
    skillsStr = JSON.stringify(data.skills);
  }

  if (skillsStr) {
    html += `
      <h2>Skills & Technical Expertise</h2>
      <p>${escapeHtml(skillsStr)}</p>
    `;
  }

  paper.innerHTML = html;
}

function saveResumeData() {
  collectFormDataWithoutRebuilding();
  const btn = document.getElementById('save-resume-btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Saving...`;
  }

  fetch(`/api/resume/${currentResumeId}/update`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      parsed_data: currentResumeData
    })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-save"></i> Save Changes`;
    }
    if (data.success) {
      showToast('Resume saved and ATS re-scored successfully!', 'success');
      if (data.analysis) {
        updateEditorAtsMeter(data.analysis);
      }
    } else {
      showToast(data.error || 'Failed to save resume', 'error');
    }
  })
  .catch(err => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-save"></i> Save Changes`;
    }
    showToast('Error saving resume', 'error');
  });
}

function exportPdf() {
  window.open(`/api/resume/${currentResumeId}/export/pdf`, '_blank');
}

function updateEditorAtsMeter(analysis) {
  const scoreVal = document.getElementById('editor-ats-score-val');
  if (scoreVal) {
    scoreVal.textContent = Math.round(analysis.ats_score || 0);
  }
}

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
