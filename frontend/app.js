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

// ── 24h-Zeit-Dropdowns (europäisches Format, kein AM/PM) ─────────────────────

// Erzeugt Optionen 00:00 .. 23:30 in 30-Minuten-Schritten
function buildTimeOptions() {
  const opts = [];
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 30) {
      const v = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
      opts.push(v);
    }
  }
  return opts;
}

// Füllt alle <select class="time-select"> mit 24h-Zeiten
function populateTimeSelects() {
  const opts = buildTimeOptions();
  document.querySelectorAll('select.time-select').forEach(sel => {
    if (sel.dataset.filled) return;
    sel.innerHTML = opts.map(v => `<option value="${v}">${v}</option>`).join('');
    sel.dataset.filled = '1';
  });
}

// Setzt den Wert eines Zeit-Dropdowns; fügt den Wert hinzu, falls er nicht im Raster liegt
function setTimeSelect(id, value) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const v = (value || '').slice(0, 5);
  if (v && !Array.from(sel.options).some(o => o.value === v)) {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  }
  sel.value = v;
}

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

// Hinweis: KEINE eigene confirm()-Funktion definieren! Eine Funktion namens
// "confirm" würde das eingebaute window.confirm überschreiben und sich selbst
// endlos aufrufen. Wir verwenden direkt das native confirm().

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
  const industryLabels = { restaurant: '🍽️ Restaurant', retail: '🛒 Einzelhandel', factory: '🏭 Fabrik', logistics: '🚚 Logistik', automotive: '🔧 Werkstatt/Autohaus' };
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
    const [shifts, reqs, absences] = await Promise.all([
      api('GET', `/api/businesses/${state.businessId}/schedule?week_start=${weekISO}`),
      api('GET', `/api/businesses/${state.businessId}/shift-requirements`),
      api('GET', `/api/businesses/${state.businessId}/absences`),
    ]);

    const understaffed = shifts.filter(s => s.is_understaffed);

    // Stunden pro Mitarbeiter + Gesamtstunden berechnen
    const empHours = {};
    let totalHours = 0;
    state.employees.forEach(e => { empHours[e.id] = 0; });
    shifts.forEach(s => {
      const dur = shiftHours(s.start_time?.slice(0,5), s.end_time?.slice(0,5));
      s.assignments.forEach(a => {
        if (empHours[a.employee_id] !== undefined) empHours[a.employee_id] += dur;
        totalHours += dur;
      });
    });

    // Abdeckung in % (zugeteilte / benötigte Plätze)
    const reqSum = shifts.reduce((acc, s) => acc + s.required_count, 0);
    const assignedSum = shifts.reduce((acc, s) => acc + s.assigned_count, 0);
    const coverage = reqSum > 0 ? Math.round((assignedSum / reqSum) * 100) : 0;

    document.getElementById('stat-employees').textContent = state.employees.filter(e => e.is_active).length;
    document.getElementById('stat-requirements').textContent = reqs.length;
    document.getElementById('stat-shifts').textContent = shifts.length;
    document.getElementById('stat-understaffed').textContent = understaffed.length;
    document.getElementById('stat-coverage').textContent = shifts.length > 0 ? coverage + '%' : '–';
    document.getElementById('stat-hours').textContent = shifts.length > 0 ? totalHours.toFixed(0) + 'h' : '–';

    document.getElementById('dash-week-info').textContent =
      `Aktuelle Woche: ${fmtDate(state.currentWeekStart)} – ${fmtDate(new Date(state.currentWeekStart.getTime() + 6 * 86400000))} (KW ${isoWeek(state.currentWeekStart)})`;

    renderUtilization(empHours, shifts.length > 0);
    renderUpcomingAbsences(absences);

    // Mini schedule preview
    const preview = document.getElementById('dashboard-schedule-preview');
    if (shifts.length === 0) {
      preview.innerHTML = '<div class="empty-state"><div class="icon">📅</div><p>Noch kein Schichtplan für diese Woche. Klicke auf „Wochenplan erstellen".</p></div>';
      return;
    }

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

// Team-Auslastung als Balken (Stunden vs. Zielstunden)
function renderUtilization(empHours, hasPlan) {
  const el = document.getElementById('dash-utilization');
  const emps = state.employees.filter(e => e.is_active);
  if (emps.length === 0) {
    el.innerHTML = '<p class="text-muted text-sm">Keine Mitarbeiter angelegt.</p>';
    return;
  }
  if (!hasPlan) {
    el.innerHTML = '<p class="text-muted text-sm">Noch kein Plan erstellt – erstelle einen Wochenplan, um die Auslastung zu sehen.</p>';
    return;
  }
  el.innerHTML = emps.map(e => {
    const h = empHours[e.id] || 0;
    const target = e.target_hours_per_week || 0;
    const max = e.max_hours_per_week || target || 1;
    const pct = Math.min(100, Math.round((h / max) * 100));
    let cls = '';
    if (target && h >= target) cls = 'full';
    if (max && h > max) cls = 'over';
    return `
      <div class="util-row">
        <span class="util-name">${e.name}</span>
        <span class="util-bar-track"><span class="util-bar-fill ${cls}" style="width:${pct}%"></span></span>
        <span class="util-val">${h.toFixed(1)} / ${target}h</span>
      </div>`;
  }).join('');
}

// Anstehende Abwesenheiten (ab heute)
function renderUpcomingAbsences(absences) {
  const el = document.getElementById('dash-absences');
  const todayISO = fmtDateISO(new Date());
  const upcoming = absences
    .filter(a => a.end_date >= todayISO)
    .sort((a, b) => a.start_date.localeCompare(b.start_date))
    .slice(0, 6);
  if (upcoming.length === 0) {
    el.innerHTML = '<p class="text-muted text-sm">Keine anstehenden Abwesenheiten. 🎉</p>';
    return;
  }
  const typeColors = { vacation: 'badge-blue', sick: 'badge-red', school: 'badge-orange', other: 'badge-gray' };
  el.innerHTML = upcoming.map(a => {
    const emp = state.employees.find(e => e.id === a.employee_id);
    return `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;font-size:13px;">
        <span class="badge ${typeColors[a.absence_type] || 'badge-gray'}">${ABSENCE_LABELS[a.absence_type]}</span>
        <b>${emp?.name || a.employee_id}</b>
        <span class="text-muted">${fmtDate(a.start_date)} – ${fmtDate(a.end_date)}</span>
      </div>`;
  }).join('');
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
  setTimeSelect('avail-from', '09:00');
  setTimeSelect('avail-until', '22:00');
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
}

// Schedule-Filter befüllen OHNE die aktuelle Auswahl zu verlieren (Fix für Filter-Bug)
function populateScheduleFilters() {
  const sfArea = document.getElementById('schedule-filter-area');
  const curArea = sfArea.value;
  sfArea.innerHTML = '<option value="">Alle</option>' +
    state.areas.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
  sfArea.value = curArea;

  const sfEmp = document.getElementById('schedule-filter-emp');
  const curEmp = sfEmp.value;
  sfEmp.innerHTML = '<option value="">Alle</option>' +
    state.employees.map(e => `<option value="${e.id}">${e.name}</option>`).join('');
  sfEmp.value = curEmp;
}

function reqChip(r) {
  const opacity = r.is_active ? '' : 'opacity:.45;';
  const rangeNote = (r.valid_from || r.valid_until)
    ? `<br><small style="color:var(--gray-500);">${r.valid_from ? fmtDate(r.valid_from) : '…'} – ${r.valid_until ? fmtDate(r.valid_until) : '…'}</small>`
    : '';
  return `
    <div class="req-chip" style="${opacity}" onclick="editRequirement(${r.id})" title="Bearbeiten">
      <button class="req-chip-del" onclick="event.stopPropagation();deleteRequirement(${r.id})" title="Löschen">✕</button>
      <div class="req-chip-time">${r.start_time?.slice(0,5)}–${r.end_time?.slice(0,5)}</div>
      <div class="req-chip-area">${r.area?.name || '–'}${r.role ? ` · ${r.role.name}` : ''}</div>
      <div class="req-chip-count">👤 ${r.required_count} Pers.${r.is_daily ? ' · täglich' : ''}</div>
      ${rangeNote}
    </div>`;
}

function renderRequirementsTable(reqs) {
  const cal = document.getElementById('req-calendar');
  const onetimeEl = document.getElementById('req-onetime');

  if (reqs.length === 0) {
    cal.innerHTML = '<div class="empty-state"><div class="icon">📋</div><p>Noch keine Schichtanforderungen.<br>Klicke auf „+ Anforderung hinzufügen".</p></div>';
    onetimeEl.innerHTML = '';
    return;
  }

  // Wochentag-basierte + tägliche Anforderungen in 7 Spalten
  const byDay = Array.from({ length: 7 }, () => []);
  const onetime = [];
  reqs.forEach(r => {
    if (r.specific_date) {
      onetime.push(r);
    } else if (r.is_daily) {
      for (let i = 0; i < 7; i++) byDay[i].push(r);
    } else if (r.weekday !== null && r.weekday !== undefined) {
      byDay[r.weekday].push(r);
    }
  });

  // nach Startzeit sortieren
  byDay.forEach(list => list.sort((a, b) => (a.start_time || '').localeCompare(b.start_time || '')));

  let head = '';
  let body = '';
  for (let i = 0; i < 7; i++) {
    head += `<th>${WEEKDAYS_DE[i]}</th>`;
    body += `<td>${byDay[i].map(reqChip).join('') || '<span class="roster-free">–</span>'}</td>`;
  }

  cal.innerHTML = `<div class="roster-wrap"><table class="roster-table req-cal-table">
    <thead><tr>${head}</tr></thead><tbody><tr>${body}</tr></tbody></table></div>`;

  // Einmalige Termine als Liste
  if (onetime.length > 0) {
    onetime.sort((a, b) => (a.specific_date || '').localeCompare(b.specific_date || ''));
    onetimeEl.innerHTML = `<div class="card" style="margin-top:20px;">
      <div class="card-title">📌 Einmalige Termine</div>
      <div class="req-onetime-grid">
        ${onetime.map(r => `<div><b>${fmtDate(r.specific_date)}</b> (${WEEKDAYS_DE[new Date(r.specific_date + 'T00:00:00').getDay() === 0 ? 6 : new Date(r.specific_date + 'T00:00:00').getDay() - 1]})${reqChip(r)}</div>`).join('')}
      </div>
    </div>`;
  } else {
    onetimeEl.innerHTML = '';
  }
}

document.getElementById('btn-add-requirement').addEventListener('click', () => {
  document.getElementById('req-id').value = '';
  document.getElementById('req-weekday').value = 'daily';
  document.getElementById('req-date').value = '';
  document.getElementById('req-valid-from').value = '';
  document.getElementById('req-valid-until').value = '';
  setTimeSelect('req-start', '10:00');
  setTimeSelect('req-end', '15:00');
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
  document.getElementById('req-weekday').value = r.is_daily ? 'daily'
    : (r.weekday !== null && r.weekday !== undefined ? r.weekday : '');
  document.getElementById('req-date').value = r.specific_date || '';
  document.getElementById('req-valid-from').value = r.valid_from || '';
  document.getElementById('req-valid-until').value = r.valid_until || '';
  setTimeSelect('req-start', r.start_time || '');
  setTimeSelect('req-end', r.end_time || '');
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
  if (end === start) { toast('Start- und Endzeit dürfen nicht identisch sein', 'error'); return; }

  const weekdayVal = document.getElementById('req-weekday').value;
  const dateVal = document.getElementById('req-date').value;
  const roleVal = document.getElementById('req-role').value;
  const isDaily = weekdayVal === 'daily';
  const isSpecificDate = weekdayVal === '';

  if (isSpecificDate && !dateVal) { toast('Bitte ein Datum wählen oder eine Wiederholung auswählen', 'error'); return; }

  const payload = {
    area_id: parseInt(areaId),
    role_id: roleVal ? parseInt(roleVal) : null,
    is_daily: isDaily,
    weekday: (!isDaily && !isSpecificDate) ? parseInt(weekdayVal) : null,
    specific_date: isSpecificDate && dateVal ? dateVal : null,
    valid_from: !isSpecificDate ? (document.getElementById('req-valid-from').value || null) : null,
    valid_until: !isSpecificDate ? (document.getElementById('req-valid-until').value || null) : null,
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

// Dauer einer Schicht in Stunden (berücksichtigt Schichten über Mitternacht)
function shiftHours(start, end) {
  if (!start || !end) return 0;
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  let s = sh + sm / 60, e = eh + em / 60;
  if (e <= s) e += 24;
  return e - s;
}

async function renderSchedule() {
  if (!state.businessId) return;
  updateWeekLabel();
  await loadBusinessMeta();
  populateScheduleFilters();

  const weekISO = fmtDateISO(state.currentWeekStart);
  const shifts = await api('GET', `/api/businesses/${state.businessId}/schedule?week_start=${weekISO}`);

  const filterEmp = parseInt(document.getElementById('schedule-filter-emp').value) || null;
  const filterArea = parseInt(document.getElementById('schedule-filter-area').value) || null;

  renderRosterMatrix(shifts, filterEmp, filterArea);
  renderScheduleWarnings(shifts);
}

// Übersichtlicher Wochenkalender: Zeilen = Mitarbeiter, Spalten = Mo–So
function renderRosterMatrix(shifts, filterEmp, filterArea) {
  const grid = document.getElementById('schedule-week-grid');
  grid.style.display = 'block';
  const todayISO = fmtDateISO(new Date());

  if (shifts.length === 0) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">🗓️</div>' +
      '<p>Noch kein Schichtplan für diese Woche.<br>Klicke oben auf „Plan erstellen".</p></div>';
    return;
  }

  // Wochentage (ISO-Datum) berechnen
  const days = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(state.currentWeekStart);
    d.setDate(d.getDate() + i);
    days.push(fmtDateISO(d));
  }

  // Mitarbeiter, die angezeigt werden
  let emps = state.employees.filter(e => e.is_active);
  if (filterEmp) emps = emps.filter(e => e.id === filterEmp);

  // Map: empId -> [Tag0..Tag6] -> [shifts], plus Stundensumme
  const map = {}, hours = {};
  emps.forEach(e => { map[e.id] = Array.from({ length: 7 }, () => []); hours[e.id] = 0; });

  // Welche Tage haben überhaupt Schichten? (geschlossene Tage werden ausgeblendet)
  const activeDays = new Set();
  shifts.forEach(s => {
    if (filterArea && s.area_id !== filterArea) return;
    const di = days.indexOf(s.date);
    if (di < 0) return;
    activeDays.add(di);
    s.assignments.forEach(a => {
      if (!map[a.employee_id]) return;
      map[a.employee_id][di].push(s);
      hours[a.employee_id] += shiftHours(s.start_time?.slice(0,5), s.end_time?.slice(0,5));
    });
  });
  const dayIdx = [...activeDays].sort((a, b) => a - b);

  if (dayIdx.length === 0) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">🗓️</div><p>Keine Schichten für die aktuelle Auswahl.</p></div>';
    return;
  }

  // Kopfzeile (nur geöffnete Tage)
  let head = '<th class="emp-col">Mitarbeiter</th>';
  dayIdx.forEach(i => {
    const d = new Date(state.currentWeekStart);
    d.setDate(d.getDate() + i);
    const isToday = days[i] === todayISO;
    head += `<th class="${isToday ? 'today-col' : ''}">${WEEKDAYS_DE[i].slice(0,2)}<br>` +
      `<span class="day-date">${d.getDate()}.${d.getMonth() + 1}.</span></th>`;
  });
  head += '<th class="sum-col">Σ Std.</th>';

  // Datenzeilen
  let rows = '';
  emps.forEach(e => {
    let row = `<td class="emp-name">${e.name}<br><span class="emp-meta">${LEVEL_BADGES[e.experience_level] || ''}</span></td>`;
    dayIdx.forEach(i => {
      const cellShifts = map[e.id][i];
      const isToday = days[i] === todayISO;
      const chips = cellShifts.map(s =>
        `<span class="roster-chip ${s.is_understaffed ? 'understaffed' : ''}" title="${s.area?.name || ''}${s.role ? ' · ' + s.role.name : ''}">
          ${s.start_time?.slice(0,5)}–${s.end_time?.slice(0,5)}<br><small>${s.area?.name || ''}</small>
        </span>`).join('');
      row += `<td class="${isToday ? 'today-col-cell' : ''}">${chips || '<span class="roster-free">frei</span>'}</td>`;
    });
    const h = hours[e.id];
    const target = e.target_hours_per_week || 0;
    const over = target && h > e.max_hours_per_week;
    row += `<td class="roster-hours ${over ? 'over' : ''}">${h.toFixed(1)}h<br><span class="hours-target">/ ${target}h</span></td>`;
    rows += `<tr>${row}</tr>`;
  });

  grid.innerHTML = `<div class="roster-wrap"><table class="roster-table">
    <thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderScheduleWarnings(shifts) {
  const warnings = shifts.filter(s => s.is_understaffed);
  const warnEl = document.getElementById('schedule-warnings');
  if (warnings.length === 0) {
    warnEl.innerHTML = shifts.length > 0
      ? '<div class="card" style="border-color:var(--success);"><div class="card-title" style="color:var(--success);">✅ Alle Schichten vollständig besetzt</div></div>'
      : '';
    return;
  }
  warnEl.innerHTML = `
    <div class="card" style="border-color:var(--danger);">
      <div class="card-title" style="color:var(--danger);">⚠️ Unterbesetzte Schichten (${warnings.length})</div>
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

async function generateSchedule() {
  if (!state.businessId) { toast('Bitte zuerst einen Betrieb auswählen', 'error'); return; }
  const weekISO = fmtDateISO(state.currentWeekStart);

  try {
    const result = await api('POST', `/api/businesses/${state.businessId}/schedule/generate`, { week_start: weekISO });
    toast(`Plan erstellt: ${result.shifts_created} Schichten, ${result.assignments_made} Zuweisungen`, 'success');
    if (result.understaffed_count > 0) {
      toast(`⚠️ ${result.understaffed_count} Schichten unterbesetzt`, 'info');
    }
    // Direkt zum Schichtplan-Kalender springen, damit man das Ergebnis sofort sieht
    navigate('schedule');
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
  // 24h-Zeit-Dropdowns füllen
  populateTimeSelects();
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
