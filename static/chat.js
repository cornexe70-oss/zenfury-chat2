(() => {
  const $ = (s) => document.querySelector(s);
  const root = document.documentElement;
  const shell = $('.app-shell');
  const usersEl = $('#user-list');
  const messagesEl = $('#messages');
  const input = $('#message-input');
  const sendBtn = $('#send-btn');
  const form = $('#send-form');
  const search = $('#search-users');
  let me = null, users = [], selected = null, lastId = 0, poller = null, seenIds = new Set();

  const savedTheme = localStorage.getItem('zenfury-theme');
  if (savedTheme === 'light' || savedTheme === 'dark') root.dataset.theme = savedTheme;
  else root.dataset.theme = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';

  function toggleTheme() {
    root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('zenfury-theme', root.dataset.theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = root.dataset.theme === 'light' ? '#eef5f1' : '#08100e';
  }
  $('#theme-toggle').addEventListener('click', toggleTheme);
  $('#header-theme').addEventListener('click', toggleTheme);

  function initials(name) { return (name || '?').trim().slice(0,1).toUpperCase(); }
  function shortTime(value) {
    if (!value) return '';
    const d = new Date(value.replace(' ', 'T') + 'Z');
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  }
  async function api(url, options={}) {
    const res = await fetch(url, {credentials:'same-origin', ...options, headers:{'Content-Type':'application/json', ...(options.headers||{})}});
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Permintaan gagal.');
    return data;
  }
  function renderUsers() {
    const q = search.value.trim().toLowerCase();
    const filtered = users.filter(u => u.username.toLowerCase().includes(q));
    $('#user-count').textContent = String(users.length);
    usersEl.replaceChildren();
    if (!filtered.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-users';
      empty.textContent = users.length ? 'Tidak ada pengguna yang cocok.' : 'Belum ada pengguna lain. Buat akun kedua di perangkat lain untuk mulai chat.';
      usersEl.append(empty);
      return;
    }
    filtered.forEach(u => {
      const btn = document.createElement('button');
      btn.className = 'user-row' + (selected && selected.id === u.id ? ' active' : '');
      const avatar = document.createElement('span'); avatar.className = 'avatar'; avatar.textContent = initials(u.username);
      const info = document.createElement('span'); info.className = 'user-info';
      const name = document.createElement('strong'); name.textContent = u.username;
      const preview = document.createElement('small'); preview.textContent = u.last_message || 'Mulai percakapan';
      const time = document.createElement('span'); time.className='time'; time.textContent=shortTime(u.last_time);
      info.append(name, preview); btn.append(avatar, info, time);
      btn.addEventListener('click', () => selectUser(u));
      usersEl.append(btn);
    });
  }
  function showWelcome() {
    messagesEl.replaceChildren();
    const card = document.createElement('div'); card.className='welcome-card glass-inner';
    const logo = document.createElement('div'); logo.className='welcome-logo'; logo.textContent='Z';
    const title = document.createElement('h2'); title.append('Welcome to ');
    const span = document.createElement('span'); span.textContent='ZENFURY'; title.append(span);
    const p = document.createElement('p'); p.textContent='Pilih pengguna di sebelah kiri untuk memulai obrolan.';
    const small = document.createElement('small'); small.textContent='Pesan tersimpan di database server.';
    card.append(logo,title,p,small); messagesEl.append(card);
  }
  function addMessage(m) {
    if (seenIds.has(m.id)) return;
    seenIds.add(m.id); lastId = Math.max(lastId, m.id);
    const mine = m.sender_id === me.id;
    const row = document.createElement('div'); row.className='message-row'+(mine?' mine':'');
    const bubble = document.createElement('div'); bubble.className='bubble'; bubble.textContent=m.body;
    const meta = document.createElement('div'); meta.className='message-meta'; meta.textContent=(mine?'Kamu':m.sender)+' · '+shortTime(m.created_at);
    row.append(bubble,meta); messagesEl.append(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  async function loadMessages() {
    if (!selected) return;
    try {
      const rows = await api(`/api/messages/${selected.id}?after=${lastId}`);
      rows.forEach(addMessage);
    } catch (e) { $('#chat-status').textContent = e.message; }
  }
  async function selectUser(user) {
    selected = user; lastId = 0; seenIds = new Set();
    shell.classList.add('chat-open');
    $('#chat-name').textContent = user.username;
    $('#chat-status').textContent = 'Percakapan pribadi';
    $('#chat-avatar').textContent = initials(user.username);
    input.disabled = false; sendBtn.disabled = false; input.placeholder = 'Ketik pesan...';
    messagesEl.replaceChildren();
    const divider = document.createElement('div'); divider.className='day-divider';
    const label = document.createElement('span'); label.textContent='MULAI OBROLAN'; divider.append(label); messagesEl.append(divider);
    renderUsers();
    await loadMessages();
    input.focus();
    if (poller) clearInterval(poller);
    poller = setInterval(loadMessages, 2200);
  }
  async function refreshUsers() {
    try { users = await api('/api/users'); renderUsers(); }
    catch(e) { usersEl.textContent = e.message; }
  }
  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (!selected) return;
    const body = input.value.trim();
    if (!body) return;
    input.value=''; sendBtn.disabled=true;
    try {
      const message = await api(`/api/messages/${selected.id}`, {method:'POST', body:JSON.stringify({body})});
      addMessage(message);
      await refreshUsers();
    } catch(err) {
      input.value = body;
      alert(err.message);
    } finally {
      sendBtn.disabled = !selected;
      input.focus();
    }
  });
  $('#emoji-btn').addEventListener('click', () => {
    input.value += '🙂';
    input.focus();
    sendBtn.disabled = !selected || !input.value.trim();
  });
  input.addEventListener('input', () => sendBtn.disabled = !selected || !input.value.trim());
  search.addEventListener('input', renderUsers);
  $('#mobile-back').addEventListener('click', () => shell.classList.remove('chat-open'));

  (async () => {
    try {
      me = await api('/api/me');
      await refreshUsers();
      setInterval(refreshUsers, 8000);
      showWelcome();
    } catch (e) { window.location.href = '/'; }
  })();
})();
