// ── State ────────────────────────────────────────────────────────────────────
let activeFilters = { status: '', priority: '', category: '', search: '' };
let editingId = null;
let editingCurrentStatus = null;
let selectedStatus = null;

const TRANSITIONS = {
  'Pending':     ['In Progress', 'Cancelled'],
  'In Progress': ['Completed', 'Pending', 'Cancelled'],
  'Completed':   ['Pending'],
  'Cancelled':   ['Pending'],
};
const STATUS_COLORS = {
  'Pending':     'var(--amber)',
  'In Progress': 'var(--purple)',
  'Completed':   'var(--teal)',
  'Cancelled':   'var(--gray)',
};

// ── API helpers ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res  = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ── Toast ────────────────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className   = 'show ' + type;
  setTimeout(() => { el.className = ''; }, 2800);
}

// ── Load tasks ───────────────────────────────────────────────────────────────
async function loadTasks() {
  const search   = document.getElementById('search-input').value;
  const priority = document.getElementById('filter-priority').value;
  const category = document.getElementById('filter-category').value;
  const params   = new URLSearchParams();
  if (activeFilters.status) params.set('status',   activeFilters.status);
  if (priority)             params.set('priority', priority);
  if (category)             params.set('category', category);
  if (search)               params.set('search',   search);

  const tasks = await api('GET', '/api/tasks?' + params.toString());
  renderTable(tasks);
}

function renderTable(tasks) {
  const tbody = document.getElementById('task-tbody');
  if (!tasks.length) {
    tbody.innerHTML = `<tr><td colspan="7">
      <div class="empty-state">
        <div class="icon">📭</div>
        <h3>No tasks found</h3>
        <p>Try adjusting your filters or create a new task.</p>
      </div></td></tr>`;
    return;
  }
  tbody.innerHTML = tasks.map(t => {
    const statusKey = t.status.replace(' ', '');
    const created   = t.created_at.split(' ')[0];
    const updated   = t.updated_at.split(' ')[0];
    return `<tr>
      <td>
        <div class="task-title">${esc(t.title)}</div>
        ${t.description
          ? `<div class="task-desc">${esc(t.description.substring(0,80))}${t.description.length > 80 ? '…' : ''}</div>`
          : ''}
      </td>
      <td><span class="badge-status status-${statusKey}">${t.status}</span></td>
      <td><span class="badge-priority prio-${t.priority}">${t.priority}</span></td>
      <td><span style="font-size:12px">${esc(t.category)}</span></td>
      <td class="task-meta">${created}</td>
      <td class="task-meta">${updated}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-ghost btn-sm" onclick="openEdit(${t.id})">✏️ Edit</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTask(${t.id}, '${esc(t.title)}')">🗑</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Stats ────────────────────────────────────────────────────────────────────
async function loadStats() {
  const s = await api('GET', '/api/stats');
  document.getElementById('stat-total').textContent      = s.total;
  document.getElementById('stat-pending').textContent    = s.by_status['Pending']     || 0;
  document.getElementById('stat-inprogress').textContent = s.by_status['In Progress'] || 0;
  document.getElementById('stat-completed').textContent  = s.by_status['Completed']   || 0;
  document.getElementById('cnt-all').textContent         = s.total;
  document.getElementById('cnt-Pending').textContent     = s.by_status['Pending']     || 0;
  document.getElementById('cnt-InProgress').textContent  = s.by_status['In Progress'] || 0;
  document.getElementById('cnt-Completed').textContent   = s.by_status['Completed']   || 0;
  document.getElementById('cnt-Cancelled').textContent   = s.by_status['Cancelled']   || 0;
}

// ── Categories ───────────────────────────────────────────────────────────────
async function loadCategories() {
  const cats = await api('GET', '/api/categories');
  const sel  = document.getElementById('filter-category');
  sel.innerHTML = '<option value="">All Categories</option>' +
    cats.map(c => `<option>${esc(c)}</option>`).join('');

  const list = document.getElementById('cat-list');
  list.innerHTML = cats.map(c =>
    `<div class="nav-item" data-filter="category" data-value="${esc(c)}" onclick="setFilter(this)">
       📁 ${esc(c)}
     </div>`).join('');
}

// ── Filter ───────────────────────────────────────────────────────────────────
function setFilter(el) {
  const filterType = el.dataset.filter;
  const value      = el.dataset.value;

  document.querySelectorAll(`[data-filter="${filterType}"]`).forEach(e => e.classList.remove('active'));
  el.classList.add('active');
  activeFilters[filterType] = value;

  document.getElementById('filter-priority').value = filterType === 'priority' ? value : '';
  document.getElementById('filter-category').value = filterType === 'category' ? value : '';

  loadTasks();
}

function resetFilters() {
  activeFilters = { status: '', priority: '', category: '', search: '' };
  document.getElementById('search-input').value    = '';
  document.getElementById('filter-priority').value = '';
  document.getElementById('filter-category').value = '';
  document.querySelectorAll('[data-filter="status"]').forEach(e => e.classList.remove('active'));
  document.querySelector('[data-filter="status"][data-value=""]').classList.add('active');
  loadTasks();
}

// ── Modal ────────────────────────────────────────────────────────────────────
function openModal() {
  editingId = null; editingCurrentStatus = null; selectedStatus = null;
  document.getElementById('modal-title').textContent    = 'New Task';
  document.getElementById('modal-save-btn').textContent = 'Create Task';
  document.getElementById('f-title').value    = '';
  document.getElementById('f-desc').value     = '';
  document.getElementById('f-priority').value = 'Medium';
  document.getElementById('f-category').value = '';
  document.getElementById('modal-error').style.display       = 'none';
  document.getElementById('status-flow-section').style.display = 'none';
  document.getElementById('modal-overlay').classList.add('open');
  setTimeout(() => document.getElementById('f-title').focus(), 100);
}

async function openEdit(id) {
  const tasks = await api('GET', '/api/tasks');
  const t = tasks.find(x => x.id === id);
  if (!t) return;

  editingId            = id;
  editingCurrentStatus = t.status;
  selectedStatus       = t.status;

  document.getElementById('modal-title').textContent    = 'Edit Task';
  document.getElementById('modal-save-btn').textContent = 'Save Changes';
  document.getElementById('f-title').value    = t.title;
  document.getElementById('f-desc').value     = t.description;
  document.getElementById('f-priority').value = t.priority;
  document.getElementById('f-category').value = t.category;
  document.getElementById('modal-error').style.display = 'none';

  // Build status pills
  const section    = document.getElementById('status-flow-section');
  const pills      = document.getElementById('status-pills');
  const allowed    = TRANSITIONS[t.status] || [];
  const allStatuses = ['Pending', 'In Progress', 'Completed', 'Cancelled'];

  pills.innerHTML = allStatuses.map(s => {
    const isCurrent   = s === t.status;
    const isAvailable = allowed.includes(s);
    let cls = 'status-pill';
    if (isCurrent)   cls += ' current selected';
    else if (isAvailable) cls += ' available';
    const col = STATUS_COLORS[s];
    return `<div class="${cls}" style="background:${col}22;color:${col}"
               onclick="selectStatus('${s}', ${isAvailable || isCurrent})">${s}</div>`;
  }).join('');

  section.style.display = 'block';
  document.getElementById('modal-overlay').classList.add('open');
}

function selectStatus(s, allowed) {
  if (!allowed) return;
  selectedStatus = s;
  document.querySelectorAll('.status-pill').forEach(el => {
    const isThis = el.textContent.trim() === s;
    el.classList.toggle('selected', isThis);
  });
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modal-overlay')) return;
  document.getElementById('modal-overlay').classList.remove('open');
}

// ── Save (create or update) ───────────────────────────────────────────────────
async function saveTask() {
  const errEl    = document.getElementById('modal-error');
  errEl.style.display = 'none';

  const title    = document.getElementById('f-title').value.trim();
  const desc     = document.getElementById('f-desc').value.trim();
  const priority = document.getElementById('f-priority').value;
  const category = document.getElementById('f-category').value.trim() || 'General';

  if (!title) {
    errEl.textContent = 'Title is required.';
    errEl.style.display = 'block';
    return;
  }

  try {
    if (editingId) {
      await api('PUT', `/api/tasks/${editingId}`, {
        title, description: desc,
        status: selectedStatus || editingCurrentStatus,
        priority, category,
      });
      toast('Task updated ✓');
    } else {
      await api('POST', '/api/tasks', { title, description: desc, priority, category });
      toast('Task created ✓');
    }
    document.getElementById('modal-overlay').classList.remove('open');
    await Promise.all([loadTasks(), loadStats(), loadCategories()]);
  } catch (err) {
    errEl.textContent   = err.message;
    errEl.style.display = 'block';
  }
}

// ── Delete ───────────────────────────────────────────────────────────────────
async function deleteTask(id, title) {
  if (!confirm(`Delete "${title}"?`)) return;
  try {
    await api('DELETE', `/api/tasks/${id}`);
    toast('Task deleted', 'error');
    await Promise.all([loadTasks(), loadStats(), loadCategories()]);
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.getElementById('modal-overlay').classList.remove('open');
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); openModal(); }
});

// ── Init ─────────────────────────────────────────────────────────────────────
(async () => {
  await Promise.all([loadTasks(), loadStats(), loadCategories()]);
})();
