/* ── Smartshift Frontend ── */

const API = '';  // same origin

// ── State ──────────────────────────────────────────────────────────────────────
let state = {
  businessId: null,
  businesses: [],
  employees: [],
  roles: [],
  areas: [],
  currentWeekStart: getMonday(new Date()),
};

// ── Utilities ──────────────────────────────────────────────────────────────────

function getMonday(d) {
  const dt = new Date(d);
  const day = dt.getDay();
  const diff = dt.getDate() - day + (day === 0 ? -6 : 1);
  dt.setDate(diff);
  dt.setHours(0, 0, 0, 0);
  return dt;
}

function fmtDate(d) {
  if (!d) return '';
  const dt = typeof d === 'string' ? new Date(d + 'T00:00:00') : d;
  return dt.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function fmtDateISO(d) {
  if (!d) return '';
  const dt = typeof d === 'string' ? new Date(d + 'T00:00:00') : d;
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, '0');
  const day = String(dt.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function isoWeek(d) {
  const dt = typeof d === 'string' ? new Date(d + 'T00:00:00') : new Date(d);
  dt.setHours(0, 0, 0, 0);
  dt.setDate(dt.getDate() + 3 - (dt.getDay() + 6) % 7);
  const week1 = new Date(dt.getFullYear(), 0, 4);
  return 1 + Math.round(((dt - week1) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
}

const WEEKDAYS_DE = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];
const ABSENCE_LABELS = { vacation: 'Urlaub', sick: 'Krankheit', school: 'Schule/Uni', other: 'Sonstiges' };
const LEVEL_BADGES = {
  junior: '<span class="badge badge-blue">Junior</span>',
  normal: '<span class="badge badge-green">Normal</span>',
  senior: '<span class="badge badge-purple">Senior</span>',
};

async function api(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || JSON.stringify(err));
  }
  if (res.status === 204) return null;
  return res.json();
}

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function openModal(id) {
  document.getElementById(id).classList.add('open');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

function confirm(msg) {
  return window.confirm(msg);
}

// ── Navigation ──────────────────────────────────────────────────────────────────

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  employees: 'Mitarbeiter',
  availabilities: 'Verfügbarkeiten',
  absences: 'Abwesenheiten',
  requirements: 'Schichtanforderungen',
  schedule: 'Schichtplan',
  gemini: 'KI-Assistent',
  settings: 'Einstellungen',
};

function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');
  document.querySelector(`[data-page="${page}"]`).classList.add('active');
  document.getElementById('page-title').textContent = PAGE_TITLES[page] || page;

  // Lazy-load data when navigating
  if (state.businessId) {
    if (page === 'dashboard') loadDashboard();
    if (page === 'employees') loadEmployees();
    if (page === 'availabilities') loadAvailabilities();
    if (page === 'absences') loadAbsences();
    if (page === 'requirements') loadRequirements();
    if (page === 'schedule') renderSchedule();
  }
}

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    navigate(link.dataset.page);
  });
});

document.querySelectorAll('[data-close]').forEach(btn => {
  btn.addEventListener('click', () => closeModal(btn.dataset.close));
});

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

// ── Business Selector ──────────────────────────────────────────────────────────

async function loadBusinesses() {
  state.businesses = await api('GET', '/api/businesses');
  const sel = document.getElementById('business-select');
  sel.innerHTML = '<option value="">– Betrieb wählen –</option>';
  state.businesses.forEach(b => {
    const opt = document.createElement('option');
    opt.value = b.id;
    opt.textContent = b.name;
    sel.appendChild(opt);
  });

  if (state.businesses.length > 0 && !state.businessId) {
    sel.value = state.businesses[0].id;
    await selectBusiness(state.businesses[0].id);
  }
  renderSettingsPage();
}

async function selectBusiness(id) {
  state.businessId = parseInt(id);
  await loadBusinessMeta();
  loadDashboard();
}

async function loadBusinessMeta() {
  if (!state.businessId) return;
  [state.roles, state.areas, state.employees] = await Promise.all([
    api('GET', `/api/businesses/${state.businessId}/roles`),
    api('GET', `/api/businesses/${state.businessId}/areas`),
    api('GET', `/api/businesses/${state.businessId}/employees`),
  ]);
}

document.getElementById('business-select').addEventListener('change', async e => {
  if (e.target.value) await selectBusiness(e.target.value);
});

document.getElementById('btn-new-business').addEventListener('click', () => navigate('settings'));

// ── Settings ───────────────────────────────────────────────────────────────────

function renderSettingsPage() {
  const el = document.getElementById('settings-business-list');
  if (state.businesses.length === 0) {
    el.innerHTML = '<p class="text-muted text-sm">Noch keine Betriebe angelegt.</p>';
    return;
  }
  const industryLabels = { restaurant: '🍽️ Restaurant', retail: '🛒 Einzelhandel', factory: '🏭 Fabrik' };
  el.innerHTML = `<table><thead><tr><th>Name</th><th>Branche</th><th>Aktionen</th></tr></thead><tbody>
    ${state.businesses.map(b => `
      <tr>
        <td>${b.name}</td>
        <td>${industryLabels[b.industry] || b.industry}</td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="deleteBusiness(${b.id})">Löschen</button>
        </td>
      </tr>
    `).join('')}
  </tbody></table>`;
}

async function deleteBusiness(id) {
  if (!confirm('Betrieb und alle Daten löschen?')) return;
  try {
    await api('DELETE', `/api/businesses/${id}`);
    toast('Betrieb gelöscht', 'success');
    state.businessId = null;
    await loadBusinesses();
  } catch (e) { toast(e.message, 'error'); }
}

document.getElementById('btn-create-business').addEventListener('click', async () => {
  const name = document.getElementById('new-business-name').value.trim();
  const industry = document.getElementById('new-business-industry').value;
  if (!name) { toast('Bitte einen Namen eingeben', 'error'); return; }
  try {
    await api('POST', '/api/businesses', { name, industry, opening_hours: [] });
    toast('Betrieb angelegt', 'success');
    document.getElementById('new-business-name').value = '';
    await loadBusinesses();
  } catch (e) { toast(e.message, 'error'); }
});

// ── Dashboard ──────────────────────────────────────────────────────────────────

async function loadDashboard() {
  if (!state.businessId) return;
  const weekISO = fmtDateISO(state.currentWeekStart);

  try {
    const [shifts] = await Promise.all([
      api('GET', `/api/businesses/${state.businessId}/schedule?week_start=${weekISO}`),
    ]);

    document.getElementById('stat-employees').textContent = state.employees.filter(e => e.is_active).length;
    document.getElementById('stat-requirements').textContent = '–';
    api('GET', `/api/businesses/${state.businessId}/shift-requirements`).then(reqs => {
      document.getElementById('stat-requirements').textContent = reqs.length;
    });
    document.getElementById('stat-shifts').textContent = shifts.length;
    document.getElementById('stat-understaffed').textContent = shifts.filter(s => s.is_understaffed).length;

    document.getElementById('dash-week-info').textContent =
      `Aktuelle Woche: ${fmtDate(state.currentWeekStart)} – ${fmtDate(new Date(state.currentWeekStart.getTime() + 6 * 86400000))} (KW ${isoWeek(state.currentWeekStart)})`;

    // Mini schedule preview
    const preview = document.getElementById('dashboard-schedule-preview');
    if (shifts.length === 0) {
      preview.innerHTML = '<div class="empty-state"><div class="icon">📅</div><p>Noch kein Schichtplan für diese Woche. Klicke auf „Wochenplan erstellen".</p></div>';
      return;
    }

    const understaffed = shifts.filter(s => s.is_understaffed);
    preview.innerHTML = `
      <div class="flex gap-3 mb-4" style="flex-wrap:wrap;">
        <div><b>${shifts.length}</b> Schichten geplant</div>
        <div style="color:var(--danger)"><b>${understaffed.length}</b> unterbesetzt</div>
        <div style="color:var(--success)"><b>${shifts.length - understaffed.length}</b> vollständig besetzt</div>
      </div>
      ${understaffed.length > 0 ? `
        <div class="card" style="border-color:var(--danger);background:var(--danger-light);">
          <div class="card-title" style="color:var(--danger);">⚠️ Unterbesetzte Schichten</div>
          ${understaffed.slice(0,5).map(s => `
            <div style="margin-bottom:6px;font-size:13px;">
              <b>${fmtDate(s.date)}</b> ${s.start_time?.slice(0,5)}–${s.end_time?.slice(0,5)}
              ${s.area?.name || ''} – ${s.assigned_count}/${s.required_count} Personen
            </div>
          `).join('')}
          ${understaffed.length > 5 ? `<p class="text-sm text-muted">...und ${understaffed.length - 5} weitere</p>` : ''}
        </div>
      ` : '<div style="color:var(--success);font-weight:600;">✅ Alle Schichten vollständig besetzt!</div>'}
    `;
  } catch (e) {
    console.error(e);
  }
}

document.getElementById('dash-generate-btn').addEventListener('click', () => generateSchedule());
document.getElementById('dash-export-btn').addEventListener('click', () => exportCSV());

// ── Employees ──────────────────────────────────────────────────────────────────

async function loadEmployees() {
  if (!state.businessId) return;
  state.employees = await api('GET', `/api/businesses/${state.businessId}/employees`);
  renderEmployeesTable();
}

function renderEmployeesTable() {
  const tbody = document.getElementById('employees-tbody');
  if (state.employees.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="icon">👥</div><p>Noch keine Mitarbeiter.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = state.employees.map(emp => `
    <tr>
      <td><b>${emp.name}</b></td>
      <td>${LEVEL_BADGES[emp.experience_level] || emp.experience_level}</td>
      <td>${emp.roles.map(r => `<span class="badge badge-blue">${r.name}</span>`).join(' ')}</td>
      <td>${emp.areas.map(a => `<span class="badge badge-gray">${a.name}</span>`).join(' ')}</td>
      <td>${emp.target_hours_per_week}h</td>
      <td>${emp.max_hours_per_week}h</td>
      <td>${emp.is_active ? '<span class="badge badge-green">Aktiv</span>' : '<span class="badge badge-red">Inaktiv</span>'}</td>
      <td>
        <button class="btn btn-ghost btn-sm" onclick="editEmployee(${emp.id})">✏️ Bearbeiten</button>
        <button class="btn btn-danger btn-sm" onclick="deleteEmployee(${emp.id})">🗑️</button>
      </td>
    </tr>
  `).join('');
}

document.getElementById('btn-add-employee').addEventListener('click', () => openEmployeeModal());

function openEmployeeModal(emp = null) {
  document.getElementById('modal-employee-title').textContent = emp ? 'Mitarbeiter bearbeiten' : 'Mitarbeiter hinzufügen';
  document.getElementById('emp-id').value = emp?.id || '';
  document.getElementById('emp-name').value = emp?.name || '';
  document.getElementById('emp-level').value = emp?.experience_level || 'normal';
  document.getElementById('emp-target').value = emp?.target_hours_per_week ?? 40;
  document.getElementById('emp-max').value = emp?.max_hours_per_week ?? 48;
  document.getElementById('emp-qualifications').value = emp?.qualifications || '';
  document.getElementById('emp-days-off').value = emp?.preferred_days_off || '';

  // Populate role/area selects
  const rolesSel = document.getElementById('emp-roles');
  rolesSel.innerHTML = state.roles.map(r =>
    `<option value="${r.id}" ${emp?.roles?.some(er => er.id === r.id) ? 'selected' : ''}>${r.name}</option>`
  ).join('');

  const areasSel = document.getElementById('emp-areas');
  areasSel.innerHTML = state.areas.map(a =>
    `<option value="${a.id}" ${emp?.areas?.some(ea => ea.id === a.id) ? 'selected' : ''}>${a.name}</option>`
  ).join('');

  openModal('modal-employee');
}

async function editEmployee(id) {
  const emp = await api('GET', `/api/employees/${id}`);
  openEmployeeModal(emp);
}

async function deleteEmployee(id) {
  if (!confirm('Mitarbeiter löschen?')) return;
  try {
    await api('DELETE', `/api/employees/${id}`);
    toast('Mitarbeiter gelöscht', 'success');
    await loadEmployees();
  } catch (e) { toast(e.message, 'error'); }
}

document.getElementById('btn-save-employee').addEventListener('click', async () => {
  const id = document.getElementById('emp-id').value;
  const name = document.getElementById('emp-name').value.trim();
  if (!name) { toast('Name ist Pflichtfeld', 'error'); return; }

  const roleIds = Array.from(document.getElementById('emp-roles').selectedOptions).map(o => parseInt(o.value));
  const areaIds = Array.from(document.getElementById('emp-areas').selectedOptions).map(o => parseInt(o.value));

  const payload = {
    name,
    experience_level: document.getElementById('emp-level').value,
    target_hours_per_week: parseFloat(document.getElementById('emp-target').value),
    max_hours_per_week: parseFloat(document.getElementById('emp-max').value),
    qualifications: document.getElementById('emp-qualifications').value,
    preferred_days_off: document.getElementById('emp-days-off').value,
    role_ids: roleIds,
    area_ids: areaIds,
  };

  try {
    if (id) {
      await api('PUT', `/api/employees/${id}`, payload);
      toast('Mitarbeiter aktualisiert', 'success');
    } else {
      await api('POST', `/api/businesses/${state.businessId}/employees`, payload);
      toast('Mitarbeiter angelegt', 'success');
    }
    closeModal('modal-employee');
    await loadEmployees();
    await loadBusinessMeta();
  } catch (e) { toast(e.message, 'error'); }
});

// ── Availabilities ─────────────────────────────────────────────────────────────

async function loadAvailabilities() {
  if (!state.businessId) return;
  populateEmployeeSelect('avail-filter-employee', true);
  populateEmployeeSelect('avail-employee');

  const empId = document.getElementById('avail-filter-employee').value;
  const weekVal = document.getElementById('avail-filter-week').value;

  let url = `/api/businesses/${state.businessId}/availabilities`;
  const params = [];
  if (weekVal) {
    const wStart = new Date(weekVal);
    const wEnd = new Date(weekVal);
    wEnd.setDate(wEnd.getDate() + 6);
    params.push(`start=${fmtDateISO(wStart)}`, `end=${fmtDateISO(wEnd)}`);
  }
  if (params.length) url += '?' + params.join('&');

  const avails = await api('GET', url);
  renderAvailTable(avails, empId ? parseInt(empId) : null);
}

function renderAvailTable(avails, filterEmpId) {
  const filtered = filterEmpId ? avails.filter(a => a.employee_id === filterEmpId) : avails;
  const tbody = document.getElementById('avail-tbody');
  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="icon">📅</div><p>Keine Verfügbarkeiten gefunden.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map(a => {
    const emp = state.employees.find(e => e.id === a.employee_id);
    return `
      <tr>
        <td>${emp?.name || a.employee_id}</td>
        <td>${fmtDate(a.date)}</td>
        <td>${a.is_available ? '<span class="badge badge-green">✓ Verfügbar</span>' : '<span class="badge badge-red">✗ Nicht verfügbar</span>'}</td>
        <td>${a.available_from?.slice(0,5) || '–'}</td>
        <td>${a.available_until?.slice(0,5) || '–'}</td>
        <td>${a.preferred_shift || '–'}</td>
        <td>${a.comment || '–'}</td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="deleteAvailability(${a.id})">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

function populateEmployeeSelect(selectId, withAll = false) {
  const sel = document.getElementById(selectId);
  const current = sel.value;
  sel.innerHTML = withAll ? '<option value="">Alle</option>' : '';
  state.employees.forEach(e => {
    const opt = document.createElement('option');
    opt.value = e.id;
    opt.textContent = e.name;
    sel.appendChild(opt);
  });
  if (current) sel.value = current;
}

document.getElementById('btn-add-availability').addEventListener('click', () => {
  document.getElementById('avail-id').value = '';
  document.getElementById('avail-date').value = fmtDateISO(new Date());
  document.getElementById('avail-is-available').value = 'true';
  document.getElementById('avail-from').value = '09:00';
  document.getElementById('avail-until').value = '22:00';
  document.getElementById('avail-preferred').value = '';
  document.getElementById('avail-comment').value = '';
  populateEmployeeSelect('avail-employee');
  openModal('modal-availability');
});

document.getElementById('avail-filter-employee').addEventListener('change', () => loadAvailabilities());
document.getElementById('avail-filter-week').addEventListener('change', () => loadAvailabilities());

document.getElementById('btn-save-availability').addEventListener('click', async () => {
  const empId = document.getElementById('avail-employee').value;
  const date = document.getElementById('avail-date').value;
  if (!empId || !date) { toast('Mitarbeiter und Datum sind Pflichtfelder', 'error'); return; }

  const payload = {
    employee_id: parseInt(empId),
    date,
    is_available: document.getElementById('avail-is-available').value === 'true',
    available_from: document.getElementById('avail-from').value || null,
    available_until: document.getElementById('avail-until').value || null,
    preferred_shift: document.getElementById('avail-preferred').value,
    comment: document.getElementById('avail-comment').value,
  };

  try {
    await api('POST', '/api/availabilities', payload);
    toast('Verfügbarkeit gespeichert', 'success');
    closeModal('modal-availability');
    loadAvailabilities();
  } catch (e) { toast(e.message, 'error'); }
});

async function deleteAvailability(id) {
  if (!confirm('Verfügbarkeit löschen?')) return;
  try {
    await api('DELETE', `/api/availabilities/${id}`);
    toast('Gelöscht', 'success');
    loadAvailabilities();
  } catch (e) { toast(e.message, 'error'); }
}

// ── Absences ───────────────────────────────────────────────────────────────────

async function loadAbsences() {
  if (!state.businessId) return;
  populateEmployeeSelect('abs-employee');
  const absences = await api('GET', `/api/businesses/${state.businessId}/absences`);
  renderAbsenceTable(absences);
}

function renderAbsenceTable(absences) {
  const tbody = document.getElementById('absence-tbody');
  if (absences.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><div class="icon">🏥</div><p>Keine Abwesenheiten.</p></div></td></tr>';
    return;
  }
  const typeColors = { vacation: 'badge-blue', sick: 'badge-red', school: 'badge-orange', other: 'badge-gray' };
  tbody.innerHTML = absences.map(a => {
    const emp = state.employees.find(e => e.id === a.employee_id);
    return `
      <tr>
        <td>${emp?.name || a.employee_id}</td>
        <td><span class="badge ${typeColors[a.absence_type] || 'badge-gray'}">${ABSENCE_LABELS[a.absence_type]}</span></td>
        <td>${fmtDate(a.start_date)}</td>
        <td>${fmtDate(a.end_date)}</td>
        <td>${a.comment || '–'}</td>
        <td>${a.approved ? '<span class="badge badge-green">✓ Ja</span>' : '<span class="badge badge-orange">Ausstehend</span>'}</td>
        <td>
          <button class="btn btn-ghost btn-sm" onclick="toggleAbsenceApproval(${a.id}, ${!a.approved})">${a.approved ? 'Widerrufen' : 'Genehmigen'}</button>
          <button class="btn btn-danger btn-sm" onclick="deleteAbsence(${a.id})">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

document.getElementById('btn-add-absence').addEventListener('click', () => {
  document.getElementById('abs-id').value = '';
  document.getElementById('abs-start').value = fmtDateISO(new Date());
  document.getElementById('abs-end').value = fmtDateISO(new Date());
  document.getElementById('abs-type').value = 'vacation';
  document.getElementById('abs-approved').value = 'false';
  document.getElementById('abs-comment').value = '';
  populateEmployeeSelect('abs-employee');
  openModal('modal-absence');
});

document.getElementById('btn-save-absence').addEventListener('click', async () => {
  const empId = document.getElementById('abs-employee').value;
  const start = document.getElementById('abs-start').value;
  const end = document.getElementById('abs-end').value;
  if (!empId || !start || !end) { toast('Mitarbeiter und Zeitraum sind Pflichtfelder', 'error'); return; }
  if (end < start) { toast('Ende muss nach Beginn liegen', 'error'); return; }

  const payload = {
    employee_id: parseInt(empId),
    absence_type: document.getElementById('abs-type').value,
    start_date: start,
    end_date: end,
    comment: document.getElementById('abs-comment').value,
  };

  try {
    await api('POST', '/api/absences', payload);
    toast('Abwesenheit eingetragen', 'success');
    closeModal('modal-absence');
    loadAbsences();
  } catch (e) { toast(e.message, 'error'); }
});

async function toggleAbsenceApproval(id, approved) {
  try {
    await api('PUT', `/api/absences/${id}`, { approved });
    toast(approved ? 'Genehmigt' : 'Genehmigung widerrufen', 'success');
    loadAbsences();
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteAbsence(id) {
  if (!confirm('Abwesenheit löschen?')) return;
  try {
    await api('DELETE', `/api/absences/${id}`);
    toast('Gelöscht', 'success');
    loadAbsences();
  } catch (e) { toast(e.message, 'error'); }
}

// ── Shift Requirements ─────────────────────────────────────────────────────────

async function loadRequirements() {
  if (!state.businessId) return;
  const reqs = await api('GET', `/api/businesses/${state.businessId}/shift-requirements`);
  renderRequirementsTable(reqs);
  populateAreaRoleSelects();
}

function populateAreaRoleSelects() {
  const areaSel = document.getElementById('req-area');
  areaSel.innerHTML = state.areas.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
  const roleSel = document.getElementById('req-role');
  roleSel.innerHTML = '<option value="">– keine –</option>' +
    state.roles.map(r => `<option value="${r.id}">${r.name}</option>`).join('');

  // Schedule filter selects
  const sfArea = document.getElementById('schedule-filter-area');
  sfArea.innerHTML = '<option value="">Alle</option>' +
    state.areas.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
  const sfEmp = document.getElementById('schedule-filter-emp');
  sfEmp.innerHTML = '<option value="">Alle</option>' +
    state.employees.map(e => `<option value="${e.id}">${e.name}</option>`).join('');
}

function renderRequirementsTable(reqs) {
  const tbody = document.getElementById('req-tbody');
  if (reqs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="icon">📋</div><p>Noch keine Schichtanforderungen.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = reqs.map(r => {
    const dayLabel = r.weekday !== null && r.weekday !== undefined
      ? WEEKDAYS_DE[r.weekday]
      : (r.specific_date ? fmtDate(r.specific_date) : '–');
    return `
      <tr>
        <td>${dayLabel}</td>
        <td><span class="badge badge-blue">${r.area?.name || '–'}</span></td>
        <td>${r.role ? `<span class="badge badge-gray">${r.role.name}</span>` : '–'}</td>
        <td>${r.start_time?.slice(0,5)}</td>
        <td>${r.end_time?.slice(0,5)}</td>
        <td><b>${r.required_count}</b> Pers.</td>
        <td>${r.is_active ? '<span class="badge badge-green">Aktiv</span>' : '<span class="badge badge-red">Inaktiv</span>'}</td>
        <td>
          <button class="btn btn-ghost btn-sm" onclick="editRequirement(${r.id})">✏️</button>
          <button class="btn btn-danger btn-sm" onclick="deleteRequirement(${r.id})">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

document.getElementById('btn-add-requirement').addEventListener('click', () => {
  document.getElementById('req-id').value = '';
  document.getElementById('req-weekday').value = '0';
  document.getElementById('req-date').value = '';
  document.getElementById('req-start').value = '10:00';
  document.getElementById('req-end').value = '15:00';
  document.getElementById('req-count').value = '1';
  document.getElementById('req-active').value = 'true';
  populateAreaRoleSelects();
  openModal('modal-requirement');
});

async function editRequirement(id) {
  const reqs = await api('GET', `/api/businesses/${state.businessId}/shift-requirements`);
  const r = reqs.find(x => x.id === id);
  if (!r) return;
  populateAreaRoleSelects();
  document.getElementById('req-id').value = r.id;
  document.getElementById('req-area').value = r.area_id;
  document.getElementById('req-role').value = r.role_id || '';
  document.getElementById('req-weekday').value = r.weekday !== null && r.weekday !== undefined ? r.weekday : '';
  document.getElementById('req-date').value = r.specific_date || '';
  document.getElementById('req-start').value = r.start_time?.slice(0,5) || '';
  document.getElementById('req-end').value = r.end_time?.slice(0,5) || '';
  document.getElementById('req-count').value = r.required_count;
  document.getElementById('req-active').value = String(r.is_active);
  openModal('modal-requirement');
}

document.getElementById('btn-save-requirement').addEventListener('click', async () => {
  const id = document.getElementById('req-id').value;
  const areaId = document.getElementById('req-area').value;
  const start = document.getElementById('req-start').value;
  const end = document.getElementById('req-end').value;
  if (!areaId || !start || !end) { toast('Bereich, Start- und Endzeit sind Pflichtfelder', 'error'); return; }
  if (end <= start) { toast('Endzeit muss nach Startzeit liegen', 'error'); return; }

  const weekdayVal = document.getElementById('req-weekday').value;
  const dateVal = document.getElementById('req-date').value;
  const roleVal = document.getElementById('req-role').value;

  const payload = {
    area_id: parseInt(areaId),
    role_id: roleVal ? parseInt(roleVal) : null,
    weekday: weekdayVal !== '' ? parseInt(weekdayVal) : null,
    specific_date: !weekdayVal && dateVal ? dateVal : null,
    start_time: start,
    end_time: end,
    required_count: parseInt(document.getElementById('req-count').value),
    is_active: document.getElementById('req-active').value === 'true',
  };

  try {
    if (id) {
      await api('PUT', `/api/shift-requirements/${id}`, payload);
      toast('Anforderung aktualisiert', 'success');
    } else {
      await api('POST', `/api/businesses/${state.businessId}/shift-requirements`, payload);
      toast('Anforderung angelegt', 'success');
    }
    closeModal('modal-requirement');
    loadRequirements();
  } catch (e) { toast(e.message, 'error'); }
});

async function deleteRequirement(id) {
  if (!confirm('Schichtanforderung löschen?')) return;
  try {
    await api('DELETE', `/api/shift-requirements/${id}`);
    toast('Gelöscht', 'success');
    loadRequirements();
  } catch (e) { toast(e.message, 'error'); }
}

// ── Schedule ───────────────────────────────────────────────────────────────────

function updateWeekLabel() {
  const end = new Date(state.currentWeekStart);
  end.setDate(end.getDate() + 6);
  document.getElementById('week-label').textContent =
    `KW ${isoWeek(state.currentWeekStart)} · ${fmtDate(state.currentWeekStart)} – ${fmtDate(end)}`;
}

document.getElementById('week-prev').addEventListener('click', () => {
  state.currentWeekStart = new Date(state.currentWeekStart.getTime() - 7 * 86400000);
  renderSchedule();
});

document.getElementById('week-next').addEventListener('click', () => {
  state.currentWeekStart = new Date(state.currentWeekStart.getTime() + 7 * 86400000);
  renderSchedule();
});

document.getElementById('btn-generate-schedule').addEventListener('click', generateSchedule);
document.getElementById('btn-delete-schedule').addEventListener('click', deleteSchedule);
document.getElementById('btn-export-csv').addEventListener('click', exportCSV);

document.getElementById('schedule-filter-emp').addEventListener('change', renderSchedule);
document.getElementById('schedule-filter-area').addEventListener('change', renderSchedule);

async function renderSchedule() {
  if (!state.businessId) return;
  updateWeekLabel();
  await loadBusinessMeta();
  populateAreaRoleSelects();

  const weekISO = fmtDateISO(state.currentWeekStart);
  const shifts = await api('GET', `/api/businesses/${state.businessId}/schedule?week_start=${weekISO}`);

  const filterEmp = parseInt(document.getElementById('schedule-filter-emp').value) || null;
  const filterArea = parseInt(document.getElementById('schedule-filter-area').value) || null;

  const filtered = shifts.filter(s => {
    if (filterArea && s.area_id !== filterArea) return false;
    if (filterEmp && !s.assignments.some(a => a.employee_id === filterEmp)) return false;
    return true;
  });

  const grid = document.getElementById('schedule-week-grid');
  const today = fmtDateISO(new Date());
  grid.innerHTML = '';

  for (let i = 0; i < 7; i++) {
    const d = new Date(state.currentWeekStart);
    d.setDate(d.getDate() + i);
    const dISO = fmtDateISO(d);
    const dayShifts = filtered.filter(s => s.date === dISO);

    const col = document.createElement('div');
    col.className = 'day-col';
    col.innerHTML = `
      <div class="day-header ${dISO === today ? 'today' : ''}">
        <div>${WEEKDAYS_DE[i].slice(0,2)}</div>
        <div style="font-size:13px;font-weight:400;">${d.getDate()}.${d.getMonth() + 1}.</div>
      </div>
      <div class="day-body">
        ${dayShifts.length === 0
          ? '<div style="padding:8px;color:var(--gray-300);font-size:11px;text-align:center;">–</div>'
          : dayShifts.map(s => renderShiftCard(s)).join('')
        }
      </div>
    `;
    grid.appendChild(col);
  }

  // Warnings section
  const warnings = shifts.filter(s => s.is_understaffed);
  const warnEl = document.getElementById('schedule-warnings');
  if (warnings.length === 0) {
    warnEl.innerHTML = '';
    return;
  }
  warnEl.innerHTML = `
    <div class="card" style="border-color:var(--danger);">
      <div class="card-title" style="color:var(--danger);">⚠️ Warnungen (${warnings.length} unterbesetzte Schichten)</div>
      ${warnings.map(s => `
        <div style="margin-bottom:8px;font-size:13px;padding:8px;background:var(--danger-light);border-radius:6px;">
          <b>${fmtDate(s.date)}</b> ${s.start_time?.slice(0,5)}–${s.end_time?.slice(0,5)} –
          ${s.area?.name || ''} ${s.role ? `(${s.role.name})` : ''} –
          ${s.assigned_count}/${s.required_count} Personen
          ${s.understaffed_reason ? `<br><span class="text-sm" style="color:var(--danger);">${s.understaffed_reason}</span>` : ''}
        </div>
      `).join('')}
    </div>
  `;
}

function renderShiftCard(shift) {
  const names = shift.assignments.map(a => a.employee?.name || '?').join(', ');
  const cls = shift.is_understaffed ? 'shift-card understaffed' : 'shift-card';
  return `
    <div class="${cls}">
      <div class="shift-time">${shift.start_time?.slice(0,5)}–${shift.end_time?.slice(0,5)}</div>
      <div class="shift-area">${shift.area?.name || '–'}${shift.role ? ` · ${shift.role.name}` : ''}</div>
      <div class="shift-staff">${shift.assigned_count}/${shift.required_count} · ${names || '–'}</div>
      ${shift.is_understaffed ? '<div class="shift-warn">⚠️ Unterbesetzt</div>' : ''}
    </div>
  `;
}

async function generateSchedule() {
  if (!state.businessId) { toast('Bitte zuerst einen Betrieb auswählen', 'error'); return; }
  const weekISO = fmtDateISO(state.currentWeekStart);

  try {
    const result = await api('POST', `/api/businesses/${state.businessId}/schedule/generate`, { week_start: weekISO });
    toast(`Plan erstellt: ${result.shifts_created} Schichten, ${result.assignments_made} Zuweisungen`, 'success');
    if (result.understaffed_count > 0) {
      toast(`⚠️ ${result.understaffed_count} Schichten unterbesetzt`, 'info');
    }
    await renderSchedule();
    await loadDashboard();
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteSchedule() {
  if (!state.businessId) return;
  if (!confirm('Schichtplan für diese Woche löschen?')) return;
  const weekISO = fmtDateISO(state.currentWeekStart);
  try {
    await api('DELETE', `/api/businesses/${state.businessId}/schedule?week_start=${weekISO}`);
    toast('Plan gelöscht', 'success');
    await renderSchedule();
    await loadDashboard();
  } catch (e) { toast(e.message, 'error'); }
}

function exportCSV() {
  if (!state.businessId) { toast('Bitte zuerst einen Betrieb auswählen', 'error'); return; }
  const weekISO = fmtDateISO(state.currentWeekStart);
  window.location.href = `/api/businesses/${state.businessId}/schedule/export/csv?week_start=${weekISO}`;
}

// ── Gemini ─────────────────────────────────────────────────────────────────────

document.getElementById('gemini-week-input').value = fmtDateISO(getMonday(new Date()));

document.getElementById('btn-gemini-analyze').addEventListener('click', async () => {
  if (!state.businessId) { toast('Bitte zuerst einen Betrieb auswählen', 'error'); return; }
  const week = document.getElementById('gemini-week-input').value;
  if (!week) { toast('Bitte eine Woche auswählen', 'error'); return; }

  document.getElementById('gemini-result').style.display = 'none';
  document.getElementById('gemini-loading').style.display = 'flex';

  try {
    const result = await api('POST', `/api/businesses/${state.businessId}/gemini-analysis`, { week_start: week });
    document.getElementById('gemini-result').textContent = result.analysis;
    document.getElementById('gemini-result').style.display = 'block';
    if (!result.available) {
      document.getElementById('gemini-result').style.borderColor = 'var(--warning)';
    } else {
      document.getElementById('gemini-result').style.borderColor = 'var(--primary)';
    }
  } catch (e) {
    document.getElementById('gemini-result').textContent = 'Fehler: ' + e.message;
    document.getElementById('gemini-result').style.display = 'block';
  } finally {
    document.getElementById('gemini-loading').style.display = 'none';
  }
});

// ── Init ───────────────────────────────────────────────────────────────────────

async function init() {
  // Set default week filter
  document.getElementById('avail-filter-week').value = fmtDateISO(state.currentWeekStart);
  updateWeekLabel();

  try {
    await loadBusinesses();
    navigate('dashboard');
  } catch (e) {
    toast('Backend nicht erreichbar. Bitte starte den Server.', 'error');
  }
}

init();
