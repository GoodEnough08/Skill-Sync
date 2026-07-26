/* ==========================================================================
   SkillSync AI - Frontend Application Logic (Categorized Skills & Next-Line Education)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initFileUpload();
  initJdMatcher();
  initEditor();
  initHistoryDelete();
});

/* Delete Resume from History */
function initHistoryDelete() {
  document.querySelectorAll('.delete-resume-history-btn').forEach(btn => {
    btn.onclick = (e) => {
      e.preventDefault();
      const resumeId = btn.dataset.resumeId;
      if (!confirm('Are you sure you want to delete this resume from your history?')) {
        return;
      }

      btn.disabled = true;
      btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i>`;

      fetch(`/api/resume/${resumeId}/delete`, {
        method: 'POST'
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showToast('Resume deleted from history.', 'success');
          const card = btn.closest('.glass-card');
          if (card) {
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '0';
            card.style.transform = 'scale(0.9)';
            setTimeout(() => {
              card.remove();
              if (document.querySelectorAll('.delete-resume-history-btn').length === 0) {
                window.location.reload();
              }
            }, 300);
          }
        } else {
          btn.disabled = false;
          btn.innerHTML = `<i class="fas fa-trash-can"></i> Delete`;
          showToast(data.error || 'Failed to delete resume', 'error');
        }
      })
      .catch(err => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-trash-can"></i> Delete`;
        showToast('Error deleting resume', 'error');
      });
    };
  });
}


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

  // Global AI Actions
  document.getElementById('ai-enhance-summary-btn')?.addEventListener('click', handleAiEnhanceSummary);
  document.getElementById('ai-suggest-skills-btn')?.addEventListener('click', handleAiSuggestSkills);
  document.getElementById('ai-categorize-skills-btn')?.addEventListener('click', handleAiCategorizeSkills);

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

  if (!experiences || experiences.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 1.5rem; border: 2px dashed rgba(255,255,255,0.15); border-radius: 12px; color: var(--text-muted);">
        <i class="fas fa-briefcase fa-2x" style="margin-bottom: 0.5rem; color: var(--primary); opacity: 0.7;"></i>
        <p style="font-weight: 500; margin-bottom: 0.75rem;">No work experience entries added yet.</p>
        <button type="button" class="btn btn-primary btn-sm add-exp-btn">
          <i class="fas fa-plus"></i> Add Work Experience Block
        </button>
      </div>
    `;
    bindExperienceEvents();
    return;
  }

  experiences.forEach((exp, idx) => {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.padding = '1.25rem';
    card.style.marginBottom = '1rem';
    card.style.border = '1px solid rgba(99, 102, 241, 0.25)';

    const bulletsHtml = (exp.bullets || []).map((bullet, bIdx) => `
      <div style="display:flex;gap:0.5rem;margin-bottom:0.5rem;align-items:center;flex-wrap:wrap;">
        <input type="text" class="form-control exp-bullet-input" data-exp-idx="${idx}" data-bullet-idx="${bIdx}" value="${escapeHtml(bullet)}" style="flex:1; min-width: 220px;">
        <select class="form-control bullet-mode-select" data-exp-idx="${idx}" data-bullet-idx="${bIdx}" style="width: auto; font-size: 0.8rem; padding: 0.35rem 0.5rem; background: rgba(15, 23, 42, 0.8);">
          <option value="impact">Metrics & Action</option>
          <option value="keywords">JD Keyword Match</option>
          <option value="executive">Executive Style</option>
        </select>
        <button type="button" class="btn btn-ai btn-sm enhance-bullet-btn" data-exp-idx="${idx}" data-bullet-idx="${bIdx}" title="AI Rewrite Bullet">
          <i class="fas fa-wand-magic-sparkles"></i> AI Enhance
        </button>
        <button type="button" class="btn btn-secondary btn-sm delete-bullet-btn" data-exp-idx="${idx}" data-bullet-idx="${bIdx}" style="color:#ef4444;" title="Delete Bullet">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `).join('');

    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.5rem;">
        <span style="font-weight: 700; color: var(--primary); font-size: 0.95rem;">
          <i class="fas fa-building" style="margin-right: 0.4rem;"></i> Position #${idx + 1}
        </span>
        <div style="display:flex; gap: 0.5rem;">
          <button type="button" class="btn btn-ai btn-sm generate-exp-bullets-btn" data-exp-idx="${idx}" title="Auto-Generate Achievements with AI">
            <i class="fas fa-sparkles"></i> AI Suggest Bullets
          </button>
          <button type="button" class="btn btn-secondary btn-sm delete-exp-btn" data-exp-idx="${idx}" style="color:#ef4444;">
            <i class="fas fa-trash"></i> Remove
          </button>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:0.75rem;">
        <div class="form-group">
          <label class="form-label">Job Title / Role</label>
          <input type="text" class="form-control exp-role-input" data-exp-idx="${idx}" value="${escapeHtml(exp.role || '')}" placeholder="e.g. Senior Software Engineer">
        </div>
        <div class="form-group">
          <label class="form-label">Company / Employer</label>
          <input type="text" class="form-control exp-company-input" data-exp-idx="${idx}" value="${escapeHtml(exp.company || '')}" placeholder="e.g. Google">
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:0.75rem;">
        <div class="form-group">
          <label class="form-label">Location</label>
          <input type="text" class="form-control exp-location-input" data-exp-idx="${idx}" value="${escapeHtml(exp.location || '')}" placeholder="e.g. San Francisco, CA (or Remote)">
        </div>
        <div class="form-group">
          <label class="form-label">Dates / Duration</label>
          <input type="text" class="form-control exp-dates-input" data-exp-idx="${idx}" value="${escapeHtml(exp.dates || '')}" placeholder="e.g. 2022 - Present">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label" style="display:flex; justify-content:space-between; align-items:center;">
          <span>Bullet Points & Key Achievements</span>
        </label>
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
      currentResumeData.experience.push({
        role: 'Software Engineer',
        company: 'Tech Innovators Inc.',
        location: 'San Francisco, CA',
        dates: '2023 - Present',
        bullets: ['Engineered scalable web applications and high-throughput REST APIs.']
      });
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
      if (!currentResumeData.experience[idx].bullets) currentResumeData.experience[idx].bullets = [];
      currentResumeData.experience[idx].bullets.push('Spearheaded key technical module development and optimized service response time.');
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

  // AI Suggest Bullets for specific position
  document.querySelectorAll('.generate-exp-bullets-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      const idx = parseInt(btn.dataset.expIdx);
      const exp = currentResumeData.experience[idx] || {};
      const jdText = document.getElementById('jd-textarea')?.value || '';

      btn.disabled = true;
      btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generating...`;

      fetch('/api/resume/generate-bullets', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          role: exp.role || 'Software Engineer',
          company: exp.company || 'Company',
          job_description: jdText
        })
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-sparkles"></i> AI Suggest Bullets`;
        if (data.success && data.bullets && data.bullets.length) {
          if (!currentResumeData.experience[idx].bullets) currentResumeData.experience[idx].bullets = [];
          currentResumeData.experience[idx].bullets.push(...data.bullets);
          renderExperienceForm(currentResumeData.experience);
          updatePaperPreview(currentResumeData);
          showToast(`Generated 3 high-impact achievement bullets for ${exp.role || 'Position'}!`, 'success');
        } else {
          showToast('Could not generate bullets', 'error');
        }
      })
      .catch(err => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-sparkles"></i> AI Suggest Bullets`;
        showToast('Error generating AI bullets', 'error');
      });
    };
  });

  // AI Enhance Individual Bullet Point
  document.querySelectorAll('.enhance-bullet-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      const eIdx = parseInt(btn.dataset.expIdx);
      const bIdx = parseInt(btn.dataset.bulletIdx);
      const currentBullet = currentResumeData.experience[eIdx].bullets[bIdx];

      if (!currentBullet) return;

      const cardWrapper = btn.closest('div');
      const modeSelect = cardWrapper ? cardWrapper.querySelector('.bullet-mode-select') : null;
      const selectedMode = modeSelect ? modeSelect.value : 'impact';
      const jdText = document.getElementById('jd-textarea')?.value || '';

      btn.disabled = true;
      btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i>`;

      fetch('/api/resume/enhance-bullet', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          bullet: currentBullet,
          mode: selectedMode,
          job_description: jdText
        })
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i> AI Enhance`;
        if (data.success && data.enhanced) {
          currentResumeData.experience[eIdx].bullets[bIdx] = data.enhanced;
          renderExperienceForm(currentResumeData.experience);
          updatePaperPreview(currentResumeData);
          showToast(`Bullet point rewritten (${selectedMode} mode)!`, 'success');
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

  if (!education || education.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 1.25rem; border: 2px dashed rgba(255,255,255,0.15); border-radius: 12px; color: var(--text-muted);">
        <p style="font-size: 0.9rem; margin-bottom: 0.5rem;">No education entries added.</p>
        <button type="button" class="btn btn-primary btn-sm add-edu-btn">
          <i class="fas fa-plus"></i> Add Education
        </button>
      </div>
    `;
    bindEducationEvents();
    return;
  }

  education.forEach((edu, idx) => {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.padding = '1rem';
    card.style.marginBottom = '0.75rem';

    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
        <strong style="color:var(--primary); font-size:0.9rem;">Education #${idx + 1}</strong>
        <button type="button" class="btn btn-secondary btn-sm delete-edu-btn" data-edu-idx="${idx}" style="color:#ef4444;">
          <i class="fas fa-trash"></i> Remove
        </button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:0.5rem;">
        <div class="form-group">
          <label class="form-label">Degree / Field of Study</label>
          <input type="text" class="form-control edu-degree-input" data-edu-idx="${idx}" value="${escapeHtml(edu.degree || '')}" placeholder="e.g. B.S. in Computer Science">
        </div>
        <div class="form-group">
          <label class="form-label">Institution / University</label>
          <input type="text" class="form-control edu-inst-input" data-edu-idx="${idx}" value="${escapeHtml(edu.institution || '')}" placeholder="e.g. Stanford University">
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
        <div class="form-group">
          <label class="form-label">Location / City</label>
          <input type="text" class="form-control edu-location-input" data-edu-idx="${idx}" value="${escapeHtml(edu.location || '')}" placeholder="e.g. Stanford, CA">
        </div>
        <div class="form-group">
          <label class="form-label">Dates / Graduation Year</label>
          <input type="text" class="form-control edu-dates-input" data-edu-idx="${idx}" value="${escapeHtml(edu.dates || '')}" placeholder="e.g. 2019 - 2023">
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  bindEducationEvents();
  bindFormInputListeners();
}

function bindEducationEvents() {
  document.querySelectorAll('.add-edu-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      if (!currentResumeData.education) currentResumeData.education = [];
      currentResumeData.education.push({
        degree: 'B.S. in Computer Science',
        institution: 'Stanford University',
        location: 'Stanford, CA',
        dates: '2019 - 2023'
      });
      renderEducationForm(currentResumeData.education);
      updatePaperPreview(currentResumeData);
    };
  });

  document.querySelectorAll('.delete-edu-btn').forEach(btn => {
    btn.onclick = () => {
      collectFormDataWithoutRebuilding();
      const idx = parseInt(btn.dataset.eduIdx);
      currentResumeData.education.splice(idx, 1);
      renderEducationForm(currentResumeData.education);
      updatePaperPreview(currentResumeData);
    };
  });
}

function renderSkillsForm(skills) {
  const input = document.getElementById('edit-skills');
  if (!input) return;
  if (Array.isArray(skills)) {
    input.value = skills.join(', ');
  } else if (typeof skills === 'object') {
    let all = [];
    Object.values(skills).forEach(arr => {
      if (Array.isArray(arr)) all.push(...arr);
      else if (typeof arr === 'string') all.push(arr);
    });
    input.value = all.join(', ');
    renderCategorizedSkillsBox(skills);
  } else {
    input.value = skills || '';
  }

  // Also auto-categorize in preview box if array
  if (Array.isArray(skills) && skills.length) {
    const categorized = categorizeSkillsArray(skills);
    renderCategorizedSkillsBox(categorized);
  }
}

function renderCategorizedSkillsBox(catObj) {
  const container = document.getElementById('categorized-skills-content');
  const box = document.getElementById('categorized-skills-preview');
  if (!container || !box) return;

  let html = '';
  Object.keys(catObj).forEach(cat => {
    const items = Array.isArray(catObj[cat]) ? catObj[cat].join(', ') : catObj[cat];
    if (items) {
      html += `
        <div style="margin-bottom:0.2rem;">
          <span style="font-weight:700; color:var(--primary);">${escapeHtml(cat)}:</span>
          <span style="color:var(--text-main);">${escapeHtml(items)}</span>
        </div>
      `;
    }
  });

  container.innerHTML = html;
  box.style.display = 'block';
}

function handleAiCategorizeSkills() {
  collectFormDataWithoutRebuilding();
  const btn = document.getElementById('ai-categorize-skills-btn');
  const skillsInput = document.getElementById('edit-skills');
  const rawSkills = skillsInput ? skillsInput.value : '';

  if (!rawSkills.trim()) {
    showToast('Please enter skills first.', 'warning');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Categorizing...`;
  }

  fetch('/api/resume/categorize-skills', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ skills: rawSkills })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-layer-group"></i> AI Group Categories`;
    }
    if (data.success && data.categorized) {
      currentResumeData.skills = data.categorized;
      renderCategorizedSkillsBox(data.categorized);
      updatePaperPreview(currentResumeData);
      showToast('Skills grouped into technical categories!', 'success');
    }
  })
  .catch(err => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-layer-group"></i> AI Group Categories`;
    }
    showToast('Error categorizing skills', 'error');
  });
}

/* AI Summary Generator / Enhancer Handler */
function handleAiEnhanceSummary() {
  collectFormDataWithoutRebuilding();
  const btn = document.getElementById('ai-enhance-summary-btn');
  const summaryInput = document.getElementById('edit-summary');
  const jdText = document.getElementById('jd-textarea')?.value || '';

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generating...`;
  }

  fetch('/api/resume/generate-summary', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      parsed_data: currentResumeData,
      job_description: jdText
    })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i> AI Generate Summary`;
    }
    if (data.success && data.summary) {
      currentResumeData.summary = data.summary;
      if (summaryInput) summaryInput.value = data.summary;
      updatePaperPreview(currentResumeData);
      showToast('AI Executive Summary generated successfully!', 'success');
    }
  })
  .catch(err => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i> AI Generate Summary`;
    }
    showToast('Error generating summary', 'error');
  });
}

/* AI Skill Suggester Handler */
function handleAiSuggestSkills() {
  collectFormDataWithoutRebuilding();
  const btn = document.getElementById('ai-suggest-skills-btn');
  const skillsInput = document.getElementById('edit-skills');
  const jdText = document.getElementById('jd-textarea')?.value || '';

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Analyzing...`;
  }

  fetch('/api/resume/suggest-skills', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      parsed_data: currentResumeData,
      job_description: jdText
    })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i> AI Suggest Skills`;
    }
    if (data.success && data.skills && data.skills.length) {
      const existing = skillsInput.value ? skillsInput.value.split(',').map(s => s.trim()) : [];
      const newSkills = data.skills.filter(s => !existing.includes(s));
      if (newSkills.length) {
        const updatedSkills = [...existing, ...newSkills];
        skillsInput.value = updatedSkills.join(', ');
        const categorized = categorizeSkillsArray(updatedSkills);
        currentResumeData.skills = categorized;
        renderCategorizedSkillsBox(categorized);
        updatePaperPreview(currentResumeData);
        showToast(`Added ${newSkills.length} recommended skills: ${newSkills.join(', ')}`, 'success');
      } else {
        showToast('Your skills list already contains top recommended skills!', 'info');
      }
    }
  })
  .catch(err => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i> AI Suggest Skills`;
    }
    showToast('Error suggesting skills', 'error');
  });
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

  // Collect Experience
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
  document.querySelectorAll('.exp-location-input').forEach(input => {
    const idx = parseInt(input.dataset.expIdx);
    if (currentResumeData.experience && currentResumeData.experience[idx]) {
      currentResumeData.experience[idx].location = input.value;
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
    if (currentResumeData.experience && currentResumeData.experience[eIdx] && currentResumeData.experience[eIdx].bullets && currentResumeData.experience[eIdx].bullets[bIdx] !== undefined) {
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
  document.querySelectorAll('.edu-location-input').forEach(input => {
    const idx = parseInt(input.dataset.eduIdx);
    if (currentResumeData.education && currentResumeData.education[idx]) {
      currentResumeData.education[idx].location = input.value;
    }
  });
  document.querySelectorAll('.edu-dates-input').forEach(input => {
    const idx = parseInt(input.dataset.eduIdx);
    if (currentResumeData.education && currentResumeData.education[idx]) {
      currentResumeData.education[idx].dates = input.value;
    }
  });

  // Collect Skills
  const rawSkills = getInputValue('edit-skills');
  const skillList = rawSkills.split(',').map(s => s.trim()).filter(s => s);
  currentResumeData.skills = categorizeSkillsArray(skillList);
  renderCategorizedSkillsBox(currentResumeData.skills);
}

function categorizeSkillsArray(skillsArr) {
  if (!Array.isArray(skillsArr)) return skillsArr;
  const taxonomy = {
    "Languages": ["python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "r", "scala", "sql", "html5", "css3", "bash", "shell", "powershell"],
    "Frameworks & Libraries": ["react", "react native", "next.js", "vue.js", "angular", "node.js", "express.js", "django", "flask", "fastapi", "spring boot", "asp.net", "laravel", "tailwind css", "bootstrap", "jquery", "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "opencv"],
    "Cloud & DevOps": ["aws", "amazon web services", "azure", "google cloud", "gcp", "docker", "kubernetes", "k8s", "terraform", "ansible", "ci/cd", "jenkins", "github actions", "gitlab ci", "linux", "nginx"],
    "Databases & Analytics": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite", "dynamodb", "cassandra", "snowflake", "bigquery", "apache kafka", "spark", "hadoop", "graphql", "rest api", "grpc"],
    "Tools & Methods": ["git", "github", "gitlab", "jira", "confluence", "postman", "figma", "docker desktop", "agile", "scrum", "ci/cd pipelines", "tdd", "microservices", "system design", "unit testing"]
  };

  const result = {};
  const uncategorized = [];

  skillsArr.forEach(item => {
    if (!item) return;
    const clean = item.trim();
    if (!clean) return;
    const lower = clean.toLowerCase();

    let matched = false;
    for (const [cat, keywords] of Object.entries(taxonomy)) {
      if (keywords.includes(lower)) {
        if (!result[cat]) result[cat] = [];
        if (!result[cat].includes(clean)) result[cat].push(clean);
        matched = true;
        break;
      }
    }

    if (!matched) {
      uncategorized.push(clean);
    }
  });

  if (uncategorized.length > 0) {
    result["Tools & Other Skills"] = uncategorized;
  }

  return Object.keys(result).length > 0 ? result : { "Technical Skills": skillsArr };
}

function getInputValue(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

function formatUrl(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return 'https://' + url;
}

function updatePaperPreview(data) {
  const paper = document.getElementById('paper-preview-sheet');
  if (!paper) return;

  const info = data.contact_info || {};
  const contactParts = [];

  if (info.email) {
    contactParts.push(`<a href="mailto:${escapeHtml(info.email)}">${escapeHtml(info.email)}</a>`);
  }
  if (info.phone) {
    contactParts.push(`<a href="tel:${escapeHtml(info.phone)}">${escapeHtml(info.phone)}</a>`);
  }
  if (info.location) {
    contactParts.push(`<strong>${escapeHtml(info.location)}</strong>`);
  }
  if (info.linkedin) {
    const url = formatUrl(info.linkedin);
    contactParts.push(`<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(info.linkedin)}</a>`);
  }
  if (info.github) {
    const url = formatUrl(info.github);
    contactParts.push(`<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(info.github)}</a>`);
  }

  const contactJoined = contactParts.map((item, idx) => `
    <span>${item}</span>
    ${idx < contactParts.length - 1 ? '<span style="color: #94a3b8; font-weight: bold; margin: 0 0.35rem;">•</span>' : ''}
  `).join('');

  let html = `
    <div style="text-align: center; margin-bottom: 1.5rem;">
      <h1 style="font-size: 2.1rem; font-weight: 800; color: #0f172a; margin-bottom: 0.35rem; text-align: center; letter-spacing: -0.02em;">
        ${escapeHtml(info.name || 'Candidate Name')}
      </h1>
      <div class="paper-contact" style="display: flex; justify-content: center; align-items: center; gap: 0.2rem 0.2rem; flex-wrap: wrap; text-align: center; font-size: 0.95rem; color: #475569;">
        ${contactJoined}
      </div>
    </div>
  `;


  if (data.summary) {
    html += `
      <h2>Professional Summary</h2>
      <p style="font-size: 1.02rem; line-height: 1.6;">${escapeHtml(data.summary)}</p>
    `;
  }

  if (data.experience && data.experience.length) {
    html += `<h2>Work Experience</h2>`;
    data.experience.forEach(exp => {
      const titleLine = [exp.role, exp.company].filter(Boolean).join(' — ');
      const locDatesParts = [];
      if (exp.location) locDatesParts.push(`<strong>${escapeHtml(exp.location)}</strong>`);
      if (exp.dates) locDatesParts.push(`<strong>${escapeHtml(exp.dates)}</strong>`);
      const locDatesStr = locDatesParts.join(' &nbsp;|&nbsp; ');

      html += `
        <div style="margin-bottom: 1.25rem;">
          <!-- Line 1: Role & Company -->
          <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 0.15rem;">
            ${escapeHtml(titleLine)}
          </div>
          
          <!-- Line 2: Location and Dates on NEXT line in BOLD -->
          ${locDatesStr ? `<div style="font-size: 0.95rem; font-weight: 700; color: #1e40af; margin-bottom: 0.4rem;">${locDatesStr}</div>` : ''}

          <!-- Line 3+: Bullet points in larger, highly readable font size -->
          <ul style="font-size: 1.02rem; line-height: 1.6; color: #1e293b; margin-top: 0.3rem;">
            ${(exp.bullets || []).map(b => `<li style="margin-bottom: 0.35rem;">${escapeHtml(b)}</li>`).join('')}
          </ul>
        </div>
      `;
    });
  }

  if (data.education && data.education.length) {
    html += `<h2>Education</h2>`;
    data.education.forEach(edu => {
      const titleLine = [edu.degree, edu.institution].filter(Boolean).join(' — ');
      const locDatesParts = [];
      if (edu.location) locDatesParts.push(`<strong>${escapeHtml(edu.location)}</strong>`);
      if (edu.dates) locDatesParts.push(`<strong>${escapeHtml(edu.dates)}</strong>`);
      const locDatesStr = locDatesParts.join(' &nbsp;|&nbsp; ');

      html += `
        <div style="margin-bottom: 1.1rem;">
          <!-- Line 1: Degree & Institution -->
          <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 0.15rem;">
            ${escapeHtml(titleLine)}
          </div>
          
          <!-- Line 2: Location and Dates on NEXT line in BOLD -->
          ${locDatesStr ? `<div style="font-size: 0.95rem; font-weight: 700; color: #1e40af; margin-bottom: 0.4rem;">${locDatesStr}</div>` : ''}
        </div>
      `;
    });
  }

  if (data.skills) {
    html += `<h2>Skills & Technical Expertise</h2>`;
    let catSkills = data.skills;
    if (Array.isArray(data.skills)) {
      catSkills = categorizeSkillsArray(data.skills);
    } else if (typeof data.skills !== 'object') {
      catSkills = categorizeSkillsArray(String(data.skills).split(','));
    }

    Object.keys(catSkills).forEach(cat => {
      const items = Array.isArray(catSkills[cat]) ? catSkills[cat].join(', ') : catSkills[cat];
      if (items) {
        html += `
          <div style="margin-bottom: 0.45rem; font-size: 1.02rem; line-height: 1.6; color: #1e293b;">
            <strong style="color: #0f172a; font-weight: 700;">${escapeHtml(cat)}:</strong> ${escapeHtml(items)}
          </div>
        `;
      }
    });
  }

  paper.innerHTML = html;
}

function saveResumeData() {
  collectFormDataWithoutRebuilding();
  const titleInput = document.getElementById('edit-resume-title');
  const customTitle = titleInput ? titleInput.value.trim() : '';

  const btn = document.getElementById('save-resume-btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Saving...`;
  }

  fetch(`/api/resume/${currentResumeId}/update`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      title: customTitle,
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
  const titleInput = document.getElementById('edit-resume-title');
  const customTitle = titleInput ? titleInput.value.trim() : '';
  const query = customTitle ? `?filename=${encodeURIComponent(customTitle)}` : '';
  window.open(`/api/resume/${currentResumeId}/export/pdf${query}`, '_blank');
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
