// Politeknik Student Course Management - Main Application Controller

const State = {
  user: null,
  currentTab: 'dashboard',
  students: [],
  courses: [],
  advisors: [],
  cohorts: [],
  programs: [],
  selectedStudent: null,
  plannerData: null
};

// ---------------- Toast Notifications ----------------
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ---------------- Modal Helpers ----------------
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('active');
}

// ---------------- Helpers ----------------
function formatCGPA(val) {
  const num = parseFloat(val) || 0.0;
  return num.toFixed(2);
}

function getCGPABadge(cgpa) {
  const val = parseFloat(cgpa) || 0.0;
  if (val >= 3.0) return `<span class="badge success">${val.toFixed(2)}</span>`;
  if (val >= 2.5) return `<span class="badge info">${val.toFixed(2)}</span>`;
  if (val >= 2.0) return `<span class="badge warning">${val.toFixed(2)}</span>`;
  return `<span class="badge danger">${val.toFixed(2)} (Kritikal)</span>`;
}

function getStatusBadge(status, grade = '') {
  const st = (status || '').toUpperCase();
  const gr = (grade || '').toUpperCase();
  if (st === 'LULUS' || ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'].includes(gr)) {
    return `<span class="badge lulus">LULUS ${gr ? `(${gr})` : ''}</span>`;
  }
  if (st === 'GAGAL' || ['E', 'E-', 'F'].includes(gr)) {
    return `<span class="badge gagal">GAGAL ${gr ? `(${gr})` : ''}</span>`;
  }
  if (st === 'TANGGUH' || gr === 'TANGGUH') {
    return `<span class="badge tangguh">TANGGUH</span>`;
  }
  return `<span class="badge progres">Dalam Progres</span>`;
}

// ---------------- Theme Management ----------------
function initTheme() {
  const saved = localStorage.getItem('politeknik_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeButton(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('politeknik_theme', next);
  updateThemeButton(next);
}

function updateThemeButton(theme) {
  const btn = document.getElementById('theme-toggle-btn');
  if (btn) {
    btn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
    btn.title = `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`;
  }
}

// ---------------- Authentication UI ----------------
function checkAuth() {
  const user = API.getUser();
  const authOverlay = document.getElementById('auth-overlay');
  const appContainer = document.getElementById('app-shell');

  if (!user) {
    if (authOverlay) authOverlay.style.display = 'flex';
    if (appContainer) appContainer.style.display = 'none';
  } else {
    State.user = user;
    if (authOverlay) authOverlay.style.display = 'none';
    if (appContainer) appContainer.style.display = 'flex';
    updateUserDisplay();
    loadInitialData();
  }
}

function updateUserDisplay() {
  if (!State.user) return;
  const nameEl = document.getElementById('nav-user-name');
  const roleEl = document.getElementById('nav-user-role');
  const avatarEl = document.getElementById('nav-user-avatar');
  const adminMenu = document.getElementById('nav-admin-link');

  if (nameEl) nameEl.textContent = State.user.full_name || State.user.user_id;
  if (roleEl) roleEl.textContent = State.user.role || 'Academic Advisor';
  if (avatarEl) {
    const initials = (State.user.full_name || 'U').substring(0, 2).toUpperCase();
    avatarEl.textContent = initials;
  }
  
  const isAdmin = (State.user.role || '').toLowerCase().includes('admin');
  if (adminMenu) {
    adminMenu.style.display = isAdmin ? 'flex' : 'none';
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-ic').value.trim();
  const password = document.getElementById('login-password').value.trim();
  const btn = document.getElementById('login-submit-btn');

  if (!username || !password) {
    showToast('Please enter both IC Number and password.', 'error');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Verifying...';

  try {
    const res = await API.login(username, password);
    showToast(`Welcome back, ${res.user.full_name || 'Advisor'}!`, 'success');
    checkAuth();
  } catch (err) {
    showToast(err.message || 'Login failed. Please check credentials.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const ic = document.getElementById('reg-ic').value.trim();
  const password = document.getElementById('reg-password').value.trim();
  const fullName = document.getElementById('reg-name').value.trim();
  const cohort = document.getElementById('reg-cohort').value.trim();
  const program = document.getElementById('reg-program').value.trim();

  try {
    await API.register({
      ic_number: ic,
      password: password,
      full_name: fullName,
      cohort: cohort || null,
      program: program || null
    });
    showToast('Account registered successfully! You can now log in.', 'success');
    closeModal('register-modal');
  } catch (err) {
    showToast(err.message || 'Registration failed.', 'error');
  }
}

async function handleLogout() {
  await API.logout();
  showToast('Logged out successfully.', 'info');
  checkAuth();
}

// ---------------- Mobile Drawer Navigation ----------------
function openSidebar() {
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (sidebar) sidebar.classList.add('open');
  if (backdrop) backdrop.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (sidebar) sidebar.classList.remove('open');
  if (backdrop) backdrop.classList.remove('active');
  document.body.style.overflow = '';
}

// ---------------- Tab Navigation ----------------
function switchTab(tabName) {
  State.currentTab = tabName;
  closeSidebar();

  // Desktop sidebar links
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.tab === tabName);
  });

  // Mobile bottom nav items
  document.querySelectorAll('.bottom-nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.tab === tabName);
  });

  document.querySelectorAll('.tab-view').forEach(view => {
    view.style.display = view.id === `view-${tabName}` ? 'block' : 'none';
  });

  if (tabName === 'dashboard') renderDashboard();
  if (tabName === 'students') renderStudents();
  if (tabName === 'enrollments') renderEnrollments();
  if (tabName === 'planner') renderPlanner();
  if (tabName === 'courses') renderCourses();
}

// ---------------- Data Fetching & Sync ----------------
async function loadInitialData() {
  try {
    const [students, courses, advisors, cohorts, programs] = await Promise.all([
      API.getStudents(),
      API.getCourses(),
      API.getAdvisors(),
      API.getCohorts(),
      API.getPrograms()
    ]);

    State.students = students;
    State.courses = courses;
    State.advisors = advisors;
    State.cohorts = cohorts;
    State.programs = programs;

    populateDropdowns();
    renderDashboard();
  } catch (err) {
    showToast('Error loading database records: ' + err.message, 'error');
  }
}

function populateDropdowns() {
  // Populate Programs in filter & modals
  const progSelects = [
    document.getElementById('filter-student-program'),
    document.getElementById('student-program-select'),
    document.getElementById('course-program-select'),
    document.getElementById('filter-course-program')
  ];

  progSelects.forEach(sel => {
    if (!sel) return;
    const currentVal = sel.value;
    const isFilter = sel.id.startsWith('filter-');
    sel.innerHTML = isFilter ? '<option value="">All Programs</option>' : '<option value="">Select Program</option>';
    
    const allProgs = Array.from(new Set([...State.programs, 'DEE', 'DEP', 'DKM', 'DTP', 'DGU']));
    allProgs.filter(Boolean).forEach(p => {
      const opt = document.createElement('option');
      opt.value = p;
      opt.textContent = p;
      sel.appendChild(opt);
    });
    if (currentVal) sel.value = currentVal;
  });

  // Populate Advisors
  const advSelects = [
    document.getElementById('filter-student-advisor'),
    document.getElementById('student-advisor-select')
  ];
  advSelects.forEach(sel => {
    if (!sel) return;
    const isFilter = sel.id.startsWith('filter-');
    sel.innerHTML = isFilter ? '<option value="">All Advisors</option>' : '<option value="">Assign Advisor (Optional)</option>';
    State.advisors.forEach(a => {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = `${a.name} (${a.username})`;
      sel.appendChild(opt);
    });
  });

  // Populate Cohorts
  const cohortFilter = document.getElementById('filter-course-cohort');
  if (cohortFilter) {
    cohortFilter.innerHTML = '<option value="">All Cohorts / Intakes</option>';
    State.cohorts.filter(Boolean).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      cohortFilter.appendChild(opt);
    });
  }
}

// ---------------- View: Dashboard ----------------
function renderDashboard() {
  const totalStudents = State.students.length;
  let passCount = 0;
  let criticalCount = 0;
  let totalCGPA = 0;
  let internshipEligibleCount = 0;

  State.students.forEach(s => {
    const cg = parseFloat(s.cgpa) || 0;
    totalCGPA += cg;
    if (cg >= 2.0) passCount++;
    if (cg < 2.2) criticalCount++;
    if ((parseFloat(s.total_credits) || 0) >= 90) internshipEligibleCount++;
  });

  const avgCGPA = totalStudents > 0 ? (totalCGPA / totalStudents).toFixed(2) : '0.00';
  const passRate = totalStudents > 0 ? ((passCount / totalStudents) * 100).toFixed(1) : '0.0';

  document.getElementById('dash-total-students').textContent = totalStudents;
  document.getElementById('dash-pass-rate').textContent = `${passRate}%`;
  document.getElementById('dash-avg-cgpa').textContent = avgCGPA;
  document.getElementById('dash-critical-students').textContent = criticalCount;
  document.getElementById('dash-internship-ready').textContent = internshipEligibleCount;

  // Recent / Top students table
  const tbody = document.getElementById('dash-students-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const sample = State.students.slice(0, 7);
  if (sample.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No student records found. Add students or import data.</td></tr>`;
    return;
  }

  sample.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${s.matric}</strong></td>
      <td>${s.name}</td>
      <td>${s.class_name || '-'}</td>
      <td>${s.program || '-'}</td>
      <td>${getCGPABadge(s.cgpa)}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openPlannerFor('${s.matric}')">🎯 Plan Semester</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ---------------- View: Students ----------------
function renderStudents() {
  const tbody = document.getElementById('students-tbody');
  if (!tbody) return;

  const search = (document.getElementById('search-students').value || '').toLowerCase();
  const prog = document.getElementById('filter-student-program').value;
  const adv = document.getElementById('filter-student-advisor').value;

  const filtered = State.students.filter(s => {
    const matchesSearch = !search || s.matric.toLowerCase().includes(search) || s.name.toLowerCase().includes(search) || (s.class_name || '').toLowerCase().includes(search);
    const matchesProg = !prog || (s.program || '').toUpperCase() === prog.toUpperCase();
    const matchesAdv = !adv || String(s.advisor_id) === String(adv);
    return matchesSearch && matchesProg && matchesAdv;
  });

  tbody.innerHTML = '';
  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 2rem; color: var(--text-muted);">No matching students found.</td></tr>`;
    return;
  }

  filtered.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="badge-pill">${s.matric}</span></td>
      <td><strong>${s.name}</strong></td>
      <td>${getCGPABadge(s.cgpa)}</td>
      <td>${s.class_name || '-'}</td>
      <td><span style="font-weight: 600; color: var(--accent-teal);">${s.total_credits}</span></td>
      <td>${s.current_sem_credits}</td>
      <td>Sem ${s.current_semester || 1}</td>
      <td><span class="badge purple">${s.program || '-'}</span></td>
      <td><small style="color: var(--text-secondary);">${s.advisor_name || 'Unassigned'}</small></td>
      <td style="white-space: nowrap;">
        <button class="btn btn-secondary btn-sm" onclick="openPlannerFor('${s.matric}')" title="Academic Course Planner">🎯 Plan</button>
        <button class="btn btn-secondary btn-sm" onclick="openEditStudentModal('${s.matric}')" title="Edit Student">✏️</button>
        <button class="btn btn-danger btn-sm" onclick="confirmDeleteStudent('${s.matric}')" title="Delete">🗑️</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openAddStudentModal() {
  document.getElementById('student-modal-title').textContent = '➕ Add New Student';
  document.getElementById('student-form-matric').value = '';
  document.getElementById('student-form-matric').disabled = false;
  document.getElementById('student-form-name').value = '';
  document.getElementById('student-form-class').value = '';
  document.getElementById('student-form-cgpa').value = '0.00';
  document.getElementById('student-form-semester').value = '1';
  document.getElementById('student-is-edit').value = 'false';
  openModal('student-modal');
}

function openEditStudentModal(matric) {
  const s = State.students.find(x => x.matric === matric);
  if (!s) return;

  document.getElementById('student-modal-title').textContent = `✏️ Edit Student - ${matric}`;
  document.getElementById('student-form-matric').value = s.matric;
  document.getElementById('student-form-matric').disabled = true;
  document.getElementById('student-form-name').value = s.name;
  document.getElementById('student-form-class').value = s.class_name || '';
  document.getElementById('student-form-cgpa').value = formatCGPA(s.cgpa);
  document.getElementById('student-form-semester').value = s.current_semester || 1;
  document.getElementById('student-program-select').value = s.program || '';
  if (s.advisor_id) document.getElementById('student-advisor-select').value = s.advisor_id;
  document.getElementById('student-is-edit').value = 'true';
  openModal('student-modal');
}

async function handleSaveStudent(e) {
  e.preventDefault();
  const isEdit = document.getElementById('student-is-edit').value === 'true';
  const matric = document.getElementById('student-form-matric').value.trim();
  const name = document.getElementById('student-form-name').value.trim();
  const className = document.getElementById('student-form-class').value.trim();
  const cgpa = parseFloat(document.getElementById('student-form-cgpa').value) || 0.0;
  const currentSemester = parseInt(document.getElementById('student-form-semester').value) || 1;
  const program = document.getElementById('student-program-select').value;
  const advisorId = document.getElementById('student-advisor-select').value ? parseInt(document.getElementById('student-advisor-select').value) : null;

  if (!matric || !name) {
    showToast('Matric number and Name are required.', 'error');
    return;
  }

  try {
    if (isEdit) {
      await API.updateStudent(matric, {
        name,
        class_name: className,
        cgpa,
        current_semester: currentSemester,
        program: program || null,
        advisor_id: advisorId
      });
      showToast(`Student ${matric} updated successfully.`, 'success');
    } else {
      await API.addStudent({
        matric,
        name,
        class_name: className,
        cgpa,
        current_semester: currentSemester,
        program: program || null,
        advisor_id: advisorId
      });
      showToast(`Student ${matric} created successfully.`, 'success');
    }
    closeModal('student-modal');
    State.students = await API.getStudents();
    renderStudents();
    renderDashboard();
  } catch (err) {
    showToast('Failed to save student: ' + err.message, 'error');
  }
}

async function confirmDeleteStudent(matric) {
  if (confirm(`Are you sure you want to delete student ${matric}? This will also delete their enrollment records.`)) {
    try {
      await API.deleteStudent(matric);
      showToast(`Student ${matric} deleted.`, 'info');
      State.students = await API.getStudents();
      renderStudents();
      renderDashboard();
    } catch (err) {
      showToast('Failed to delete student: ' + err.message, 'error');
    }
  }
}

async function triggerSyncMetrics() {
  const btn = document.getElementById('sync-metrics-btn');
  if (btn) btn.disabled = true;
  showToast('Synchronizing student CGPA and credits...', 'info');
  try {
    await API.syncMetrics();
    State.students = await API.getStudents();
    renderStudents();
    renderDashboard();
    showToast('All metrics synchronized successfully!', 'success');
  } catch (err) {
    showToast('Sync failed: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ---------------- View: Academic Planner ----------------
function openPlannerFor(matric) {
  switchTab('planner');
  const sel = document.getElementById('planner-student-select');
  if (sel) {
    sel.value = matric;
    loadStudentPlan(matric);
  }
}

function renderPlanner() {
  const sel = document.getElementById('planner-student-select');
  if (!sel) return;

  const currentVal = sel.value;
  sel.innerHTML = '<option value="">-- Choose a Student --</option>';
  State.students.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.matric;
    opt.textContent = `${s.matric} - ${s.name} (Sem ${s.current_semester || 1})`;
    sel.appendChild(opt);
  });

  if (currentVal) {
    sel.value = currentVal;
    loadStudentPlan(currentVal);
  } else if (State.students.length > 0) {
    sel.value = State.students[0].matric;
    loadStudentPlan(State.students[0].matric);
  }
}

async function loadStudentPlan(matric) {
  if (!matric) {
    document.getElementById('planner-details-view').style.display = 'none';
    return;
  }

  const loader = document.getElementById('planner-loader');
  const details = document.getElementById('planner-details-view');
  if (loader) loader.style.display = 'block';
  if (details) details.style.display = 'none';

  try {
    const data = await API.getPlanner(matric);
    const detailData = await API.getStudentDetails(matric);
    State.plannerData = { ...data, ...detailData };
    displayPlannerData(State.plannerData);
  } catch (err) {
    showToast('Error loading plan: ' + err.message, 'error');
  } finally {
    if (loader) loader.style.display = 'none';
    if (details) details.style.display = 'block';
  }
}

function displayPlannerData(p) {
  document.getElementById('spotlight-matric').textContent = p.matric;
  const s = State.students.find(x => x.matric === p.matric);
  document.getElementById('spotlight-name').textContent = s ? s.name : p.matric;
  document.getElementById('spotlight-prog-sem').textContent = `${s?.program || 'DEE'} • Semester ${p.current_semester} • Class: ${s?.class_name || '-'}`;
  
  // Badges
  document.getElementById('spotlight-cgpa-badge').innerHTML = getCGPABadge(p.cgpa);
  
  const internEl = document.getElementById('spotlight-internship-badge');
  if (p.internship_eligible) {
    internEl.innerHTML = `<span class="badge success">✅ Eligible for Internship (≥90 Credits)</span>`;
  } else {
    internEl.innerHTML = `<span class="badge warning">⏳ Pending Internship (${p.total_credits_earned || 0} / 90 Credits)</span>`;
  }

  // Credit Gauge & Policy
  document.getElementById('gauge-current-val').textContent = `${p.current_semester_credits || 0} hrs`;
  document.getElementById('gauge-max-val').textContent = `Max: ${p.max_credits} hrs`;
  
  const fill = document.getElementById('planner-gauge-fill');
  const percent = Math.min(100, Math.round(((p.current_semester_credits || 0) / p.max_credits) * 100));
  fill.style.width = `${percent}%`;
  fill.className = percent > 100 ? 'progress-bar-fill overload' : 'progress-bar-fill';

  // Rule Explainer
  const ruleEl = document.getElementById('planner-rule-explainer');
  let ruleText = '';
  if (p.cgpa >= 2.50) {
    ruleText = `CGPA is <strong>${p.cgpa.toFixed(2)} (≥ 2.50)</strong>: Maximum permitted credit load is <strong>18 Credit Hours</strong>.`;
  } else if (p.cgpa >= 2.20) {
    ruleText = `CGPA is <strong>${p.cgpa.toFixed(2)} (2.20 - 2.49)</strong>: Maximum permitted credit load is <strong>15 Credit Hours</strong>.`;
  } else {
    ruleText = `CGPA is <strong>${p.cgpa.toFixed(2)} (< 2.20)</strong>: Critical academic status. Maximum credit limit strictly reduced to <strong>12 Credit Hours</strong>.`;
  }
  ruleEl.innerHTML = ruleText;

  // Failed / Retake Courses
  const retakeSec = document.getElementById('retakes-section');
  const retakeList = document.getElementById('retakes-list');
  if (p.retakes_needed && p.retakes_needed.length > 0) {
    retakeSec.style.display = 'block';
    retakeList.innerHTML = p.retakes_needed.map(r => `
      <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 0.75rem 1rem; border-radius: var(--radius-md); margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <strong>${r.course_code} - ${r.course_name}</strong>
          <div style="font-size: 0.78rem; color: var(--text-muted);">Credit Hours: ${r.credit_hours} • Last Grade: <span class="badge danger">${r.last_grade || 'F'}</span> • Attempt: ${r.last_attempt || 'NORMAL'}</div>
        </div>
        <span class="badge carry">⚠️ MUST RETAKE (C1/C2)</span>
      </div>
    `).join('');
  } else {
    retakeSec.style.display = 'none';
  }

  // Recommended Future Courses Table
  const recTbody = document.getElementById('recommended-courses-tbody');
  recTbody.innerHTML = '';
  if (!p.future_recommended_courses || p.future_recommended_courses.length === 0) {
    recTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No further course recommendations available or student has completed all syllabus courses.</td></tr>`;
  } else {
    p.future_recommended_courses.forEach(c => {
      const tr = document.createElement('tr');
      const isCarry = c.is_dropped;
      const prereqOk = c.prereqs_satisfied;

      let statusHtml = '';
      if (isCarry) {
        statusHtml = `<span class="badge carry">Carry / Retake</span>`;
      } else if (prereqOk) {
        statusHtml = `<span class="badge success">Prerequisites Met</span>`;
      } else {
        statusHtml = `<span class="badge danger">Prerequisite Blocked</span>`;
      }

      tr.innerHTML = `
        <td><strong>${c.code}</strong></td>
        <td>${c.name}</td>
        <td>Sem ${c.semester}</td>
        <td><strong>${c.credits}</strong> hrs</td>
        <td>${statusHtml}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="quickEnroll('${p.matric}', '${c.code}', ${c.semester}, '${isCarry ? 'C1' : 'NORMAL'}')">➕ Enroll</button>
        </td>
      `;
      recTbody.appendChild(tr);
    });
  }

  // Student Past & Current Enrollments
  const enrTbody = document.getElementById('student-enrollments-tbody');
  enrTbody.innerHTML = '';
  if (!p.enrollments || p.enrollments.length === 0) {
    enrTbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No registered enrollment history.</td></tr>`;
  } else {
    p.enrollments.forEach(e => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${e.course_code}</td>
        <td>${e.course_name}</td>
        <td>${e.semester_session}</td>
        <td><span class="badge ${e.attempt_type === 'NORMAL' ? 'info' : 'purple'}">${e.attempt_type}</span></td>
        <td><strong>${e.grade || '-'}</strong></td>
        <td>${getStatusBadge(e.pass_status, e.grade)}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openEditEnrollmentModal(${e.id}, '${e.course_code}', '${e.course_name}', '${e.semester_session}', '${e.attempt_type}', '${e.grade}', '${e.pass_status}')">✏️ Edit</button>
        </td>
      `;
      enrTbody.appendChild(tr);
    });
  }
}

// ---------------- View: Enrollments ----------------
async function renderEnrollments() {
  const sem = document.getElementById('filter-enrollment-sem').value;
  const tbody = document.getElementById('enrollments-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Loading enrollments...</td></tr>`;

  try {
    const list = await API.getEnrollments({ semester: sem || 1 });
    tbody.innerHTML = '';
    if (list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No enrollment records found for Semester ${sem || 1}.</td></tr>`;
      return;
    }

    list.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="badge-pill">${item.student_id}</span></td>
        <td><strong>${item.student_name || item.student_id}</strong></td>
        <td><strong>${item.course_code}</strong></td>
        <td>${item.course_name}</td>
        <td>${item.semester_session}</td>
        <td><span class="badge ${item.attempt_type === 'NORMAL' ? 'info' : 'purple'}">${item.attempt_type}</span></td>
        <td><strong>${item.grade || '-'}</strong></td>
        <td>${getStatusBadge(item.pass_status, item.grade)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--status-danger);">Error: ${err.message}</td></tr>`;
  }
}

function openAddEnrollmentModal() {
  // Populate student dropdown in enrollment modal
  const studSelect = document.getElementById('enr-student-select');
  studSelect.innerHTML = '<option value="">-- Select Student --</option>';
  State.students.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.matric;
    opt.textContent = `${s.matric} - ${s.name}`;
    studSelect.appendChild(opt);
  });

  // Populate courses
  const courseSelect = document.getElementById('enr-course-select');
  courseSelect.innerHTML = '<option value="">-- Select Course --</option>';
  State.courses.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.course_code;
    opt.textContent = `${c.course_code} - ${c.course_name} (Sem ${c.default_semester})`;
    courseSelect.appendChild(opt);
  });

  document.getElementById('enr-session').value = '2025/2026-SEM1';
  document.getElementById('enr-attempt').value = 'NORMAL';
  document.getElementById('enr-grade').value = '';
  openModal('add-enrollment-modal');
}

async function quickEnroll(studentId, courseCode, sem, attempt = 'NORMAL') {
  try {
    await API.addEnrollment({
      student_id: studentId,
      course_code: courseCode,
      semester_session: `2025/2026-SEM${sem}`,
      attempt_type: attempt,
      grade: null,
      pass_status: null
    });
    showToast(`Enrolled ${studentId} into ${courseCode}!`, 'success');
    loadStudentPlan(studentId);
  } catch (err) {
    showToast('Failed to enroll: ' + err.message, 'error');
  }
}

async function handleSaveEnrollment(e) {
  e.preventDefault();
  const student_id = document.getElementById('enr-student-select').value;
  const course_code = document.getElementById('enr-course-select').value;
  const semester_session = document.getElementById('enr-session').value.trim();
  const attempt_type = document.getElementById('enr-attempt').value;
  const grade = document.getElementById('enr-grade').value.trim() || null;

  if (!student_id || !course_code || !semester_session) {
    showToast('Student, Course, and Session are required.', 'error');
    return;
  }

  try {
    await API.addEnrollment({
      student_id,
      course_code,
      semester_session,
      attempt_type,
      grade
    });
    showToast('Enrollment created successfully.', 'success');
    closeModal('add-enrollment-modal');
    renderEnrollments();
  } catch (err) {
    showToast('Failed to create enrollment: ' + err.message, 'error');
  }
}

function openEditEnrollmentModal(id, ccode, cname, session, attempt, grade, passStatus) {
  document.getElementById('edit-enr-id').value = id;
  document.getElementById('edit-enr-title').textContent = `✏️ Edit Enrollment - ${ccode}`;
  document.getElementById('edit-enr-session').value = session;
  document.getElementById('edit-enr-attempt').value = attempt;
  document.getElementById('edit-enr-grade').value = grade && grade !== '-' ? grade : '';
  openModal('edit-enrollment-modal');
}

async function handleUpdateEnrollment(e) {
  e.preventDefault();
  const id = document.getElementById('edit-enr-id').value;
  const semester_session = document.getElementById('edit-enr-session').value.trim();
  const attempt_type = document.getElementById('edit-enr-attempt').value;
  const grade = document.getElementById('edit-enr-grade').value.trim() || null;

  try {
    await API.updateEnrollment(id, {
      semester_session,
      attempt_type,
      grade
    });
    showToast('Enrollment updated successfully.', 'success');
    closeModal('edit-enrollment-modal');
    if (State.selectedStudent) {
      loadStudentPlan(State.selectedStudent);
    }
    renderEnrollments();
  } catch (err) {
    showToast('Failed to update enrollment: ' + err.message, 'error');
  }
}

// ---------------- View: Courses & Prerequisites ----------------
function renderCourses() {
  const tbody = document.getElementById('courses-tbody');
  if (!tbody) return;

  const search = (document.getElementById('search-courses').value || '').toLowerCase();
  const prog = document.getElementById('filter-course-program').value;
  const cohort = document.getElementById('filter-course-cohort').value;
  const sem = document.getElementById('filter-course-sem').value;

  const filtered = State.courses.filter(c => {
    const matchesSearch = !search || c.course_code.toLowerCase().includes(search) || c.course_name.toLowerCase().includes(search);
    const matchesProg = !prog || (c.program || '').toUpperCase() === prog.toUpperCase();
    const matchesCohort = !cohort || (c.cohort || '').toUpperCase() === cohort.toUpperCase();
    const matchesSem = !sem || String(c.default_semester) === String(sem);
    return matchesSearch && matchesProg && matchesCohort && matchesSem;
  });

  tbody.innerHTML = '';
  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No courses found.</td></tr>`;
    return;
  }

  filtered.forEach(c => {
    const prereqBadges = (c.prerequisites || []).map(p => 
      `<span class="badge info" style="margin-right: 4px;">${p} <a onclick="confirmRemovePrereq('${c.course_code}', '${p}')" style="cursor:pointer; color:inherit; margin-left:4px;">&times;</a></span>`
    ).join('') || '<span style="color:var(--text-muted); font-size:0.8rem;">None</span>';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${c.course_code}</strong></td>
      <td>${c.course_name}</td>
      <td><span class="badge-pill">Sem ${c.default_semester}</span></td>
      <td><strong>${c.credit_hours}</strong> hrs</td>
      <td><span class="badge purple">${c.program || '-'}</span></td>
      <td>${c.cohort || '-'}</td>
      <td>${prereqBadges}</td>
      <td style="white-space: nowrap;">
        <button class="btn btn-secondary btn-sm" onclick="openAddPrereqModal('${c.course_code}')" title="Add Prerequisite">🔗 Link</button>
        <button class="btn btn-secondary btn-sm" onclick="openEditCourseModal('${c.course_code}')" title="Edit">✏️</button>
        <button class="btn btn-danger btn-sm" onclick="confirmDeleteCourse('${c.course_code}')" title="Delete">🗑️</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openAddCourseModal() {
  document.getElementById('course-modal-title').textContent = '➕ Add New Course';
  document.getElementById('course-form-code').value = '';
  document.getElementById('course-form-code').disabled = false;
  document.getElementById('course-form-name').value = '';
  document.getElementById('course-form-sem').value = '1';
  document.getElementById('course-form-credits').value = '3';
  document.getElementById('course-form-cohort').value = '2025/2026';
  document.getElementById('course-is-edit').value = 'false';
  openModal('course-modal');
}

function openEditCourseModal(code) {
  const c = State.courses.find(x => x.course_code === code);
  if (!c) return;

  document.getElementById('course-modal-title').textContent = `✏️ Edit Course - ${code}`;
  document.getElementById('course-form-code').value = c.course_code;
  document.getElementById('course-form-code').disabled = true;
  document.getElementById('course-form-name').value = c.course_name;
  document.getElementById('course-form-sem').value = c.default_semester;
  document.getElementById('course-form-credits').value = c.credit_hours;
  document.getElementById('course-form-cohort').value = c.cohort || '';
  document.getElementById('course-program-select').value = c.program || '';
  document.getElementById('course-is-edit').value = 'true';
  openModal('course-modal');
}

async function handleSaveCourse(e) {
  e.preventDefault();
  const isEdit = document.getElementById('course-is-edit').value === 'true';
  const code = document.getElementById('course-form-code').value.trim();
  const name = document.getElementById('course-form-name').value.trim();
  const semester = parseInt(document.getElementById('course-form-sem').value) || 1;
  const credits = parseInt(document.getElementById('course-form-credits').value) || 3;
  const cohort = document.getElementById('course-form-cohort').value.trim();
  const program = document.getElementById('course-program-select').value;

  if (!code || !name) {
    showToast('Course code and Course name are required.', 'error');
    return;
  }

  try {
    if (isEdit) {
      await API.updateCourse(code, {
        name,
        semester,
        credits,
        cohort: cohort || null,
        program: program || null
      });
      showToast(`Course ${code} updated successfully.`, 'success');
    } else {
      await API.addCourse({
        code,
        name,
        semester,
        credits,
        cohort: cohort || null,
        program: program || null
      });
      showToast(`Course ${code} created successfully.`, 'success');
    }
    closeModal('course-modal');
    State.courses = await API.getCourses();
    renderCourses();
  } catch (err) {
    showToast('Failed to save course: ' + err.message, 'error');
  }
}

async function confirmDeleteCourse(code) {
  if (confirm(`Are you sure you want to delete course ${code}? This will also delete any related prerequisite links.`)) {
    try {
      await API.deleteCourse(code);
      showToast(`Course ${code} deleted.`, 'info');
      State.courses = await API.getCourses();
      renderCourses();
    } catch (err) {
      showToast('Failed to delete course: ' + err.message, 'error');
    }
  }
}

function openAddPrereqModal(targetCourse) {
  document.getElementById('prereq-target-course').value = targetCourse;
  document.getElementById('prereq-target-display').textContent = targetCourse;

  const sel = document.getElementById('prereq-select-code');
  sel.innerHTML = '<option value="">-- Choose Prerequisite Course --</option>';
  State.courses.filter(c => c.course_code !== targetCourse).forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.course_code;
    opt.textContent = `${c.course_code} - ${c.course_name} (Sem ${c.default_semester})`;
    sel.appendChild(opt);
  });
  openModal('prereq-modal');
}

async function handleSavePrereq(e) {
  e.preventDefault();
  const target = document.getElementById('prereq-target-course').value;
  const prereq = document.getElementById('prereq-select-code').value;

  if (!prereq) {
    showToast('Please select a prerequisite course.', 'error');
    return;
  }

  try {
    await API.addPrerequisite(target, prereq);
    showToast(`Linked ${prereq} as prerequisite for ${target}.`, 'success');
    closeModal('prereq-modal');
    State.courses = await API.getCourses();
    renderCourses();
  } catch (err) {
    showToast('Failed to link prerequisite: ' + err.message, 'error');
  }
}

async function confirmRemovePrereq(course, prereq) {
  if (confirm(`Remove prerequisite ${prereq} from ${course}?`)) {
    try {
      await API.deletePrerequisite(course, prereq);
      showToast(`Prerequisite ${prereq} removed.`, 'info');
      State.courses = await API.getCourses();
      renderCourses();
    } catch (err) {
      showToast('Failed to remove prerequisite: ' + err.message, 'error');
    }
  }
}

// ---------------- View: Import & Export ----------------
async function handleFileUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById('file-upload-input');
  if (!fileInput.files || fileInput.files.length === 0) {
    showToast('Please select an Excel (.xlsx/.xls), CSV, or PDF file to upload.', 'error');
    return;
  }

  const file = fileInput.files[0];
  const importType = document.getElementById('import-type-select').value;
  const btn = document.getElementById('upload-submit-btn');
  const resultDiv = document.getElementById('import-result-summary');

  btn.disabled = true;
  btn.textContent = 'Processing & Parsing...';

  try {
    const res = await API.importFile(file, importType);
    showToast('File imported successfully!', 'success');
    if (resultDiv) {
      resultDiv.style.display = 'block';
      resultDiv.innerHTML = `
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid var(--status-success); padding: 1rem; border-radius: var(--radius-md); color: var(--status-success);">
          <strong>🎉 Import Completed!</strong>
          <p style="margin-top: 0.25rem;">${res.message}</p>
        </div>
      `;
    }
    // Refresh all caches
    State.students = await API.getStudents();
    State.courses = await API.getCourses();
    renderDashboard();
  } catch (err) {
    showToast('Import error: ' + err.message, 'error');
    if (resultDiv) {
      resultDiv.style.display = 'block';
      resultDiv.innerHTML = `
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid var(--status-danger); padding: 1rem; border-radius: var(--radius-md); color: var(--status-danger);">
          <strong>❌ Import Failed:</strong>
          <p style="margin-top: 0.25rem;">${err.message}</p>
        </div>
      `;
    }
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload & Process Data';
  }
}

function triggerExport(type) {
  window.open(`/api/export/${type}`, '_blank');
}

// ---------------- Application Bootstrapping ----------------
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  checkAuth();

  // Mobile Drawer & Navigation Toggles
  document.getElementById('menu-toggle-btn')?.addEventListener('click', openSidebar);
  document.getElementById('close-drawer-btn')?.addEventListener('click', closeSidebar);
  document.getElementById('sidebar-backdrop')?.addEventListener('click', closeSidebar);
  document.getElementById('bottom-more-btn')?.addEventListener('click', openSidebar);

  // Mobile Bottom Navigation Links
  document.querySelectorAll('.bottom-nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const tab = item.dataset.tab;
      if (tab) switchTab(tab);
    });
  });

  // Desktop Navigation Links
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const tab = link.dataset.tab;
      if (tab) switchTab(tab);
    });
  });

  // Theme toggle
  document.getElementById('theme-toggle-btn')?.addEventListener('click', toggleTheme);

  // Auth Forms
  document.getElementById('login-form')?.addEventListener('submit', handleLogin);
  document.getElementById('register-form')?.addEventListener('submit', handleRegister);
  document.getElementById('logout-btn')?.addEventListener('click', handleLogout);

  // Student Form
  document.getElementById('student-form')?.addEventListener('submit', handleSaveStudent);

  // Course Form
  document.getElementById('course-form')?.addEventListener('submit', handleSaveCourse);

  // Prerequisite Form
  document.getElementById('prereq-form')?.addEventListener('submit', handleSavePrereq);

  // Enrollment Forms
  document.getElementById('add-enrollment-form')?.addEventListener('submit', handleSaveEnrollment);
  document.getElementById('edit-enrollment-form')?.addEventListener('submit', handleUpdateEnrollment);

  // Import Form
  document.getElementById('import-form')?.addEventListener('submit', handleFileUpload);

  // Listeners for filters
  document.getElementById('search-students')?.addEventListener('input', renderStudents);
  document.getElementById('filter-student-program')?.addEventListener('change', renderStudents);
  document.getElementById('filter-student-advisor')?.addEventListener('change', renderStudents);

  document.getElementById('search-courses')?.addEventListener('input', renderCourses);
  document.getElementById('filter-course-program')?.addEventListener('change', renderCourses);
  document.getElementById('filter-course-cohort')?.addEventListener('change', renderCourses);
  document.getElementById('filter-course-sem')?.addEventListener('change', renderCourses);

  document.getElementById('filter-enrollment-sem')?.addEventListener('change', renderEnrollments);
  document.getElementById('planner-student-select')?.addEventListener('change', (e) => loadStudentPlan(e.target.value));

  // Global Session Expired Handler
  window.addEventListener('auth:expired', () => {
    showToast('Session expired. Please log in again.', 'warning');
    checkAuth();
  });
});
