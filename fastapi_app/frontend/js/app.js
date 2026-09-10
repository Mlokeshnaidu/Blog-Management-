let token = localStorage.getItem('token');
let user = JSON.parse(localStorage.getItem('user') || 'null');
let currentTab = 'all';
let currentPostId = null;
let searchTimer = null;

function authHeaders() {
  return token ? { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` } : { 'Content-Type': 'application/json' };
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('active');
  setTimeout(() => t.classList.remove('active'), 3000);
}

function updateUI() {
  const loggedIn = Boolean(token && user);
  document.getElementById('auth-logged-out').style.display = loggedIn ? 'none' : 'flex';
  document.getElementById('auth-logged-in').style.display = loggedIn ? 'flex' : 'none';
  document.getElementById('tab-mine').style.display = loggedIn ? 'inline-block' : 'none';
  document.getElementById('btn-new-post').style.display = loggedIn ? 'inline-block' : 'none';
  if (loggedIn) document.getElementById('user-display').textContent = `@${user.username}`;
  loadPosts();
}

function setTab(tab) {
  currentTab = tab;
  document.getElementById('tab-all').classList.toggle('active', tab === 'all');
  document.getElementById('tab-mine').classList.toggle('active', tab === 'mine');
  loadPosts();
}

function debounceSearch(val) {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadPosts(val), 300);
}

async function loadPosts(query = '') {
  const url = currentTab === 'mine' ? '/posts/mine' : (query ? `/posts?q=${encodeURIComponent(query)}` : '/posts');
  try {
    const res = await fetch(url, { headers: authHeaders() });
    const posts = await res.json();
    const container = document.getElementById('posts-list');
    if (!res.ok) throw new Error(posts.detail || 'Error loading posts');

    if (!posts.length) {
      container.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:40px;">No posts found.</p>`;
      return;
    }

    container.innerHTML = posts.map(p => {
      const isOwner = user && user.id === p.author_id;
      return `
        <div class="post-card">
          <h3 onclick="openDetail(${p.id})">${escapeHtml(p.title)}</h3>
          <p>${escapeHtml(p.content.slice(0, 140))}${p.content.length > 140 ? '...' : ''}</p>
          <div class="post-meta">
            <div>By @${p.author ? escapeHtml(p.author.username) : 'Unknown'} | ${new Date(p.created_at).toLocaleDateString()}</div>
            <div class="post-stats">
              <button class="${p.is_liked_by_me ? 'liked' : ''}" onclick="likePost(${p.id})">Likes: ${p.likes_count}</button>
              <button onclick="openDetail(${p.id})">Comments: ${p.comments_count}</button>
              ${isOwner ? `
                <div class="post-card-actions">
                  <button class="btn btn-secondary btn-sm" onclick="editPost(${p.id}, '${escapeHtml(p.title)}', '${escapeHtml(p.content)}')">Edit</button>
                  <button class="btn btn-danger btn-sm" onclick="deletePost(${p.id})">Delete</button>
                </div>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    showToast(err.message);
  }
}

async function handleAuth(e) {
  e.preventDefault();
  const isReg = document.getElementById('auth-tab-register').classList.contains('active');
  const u = document.getElementById('auth-username').value;
  const p = document.getElementById('auth-password').value;
  const email = document.getElementById('auth-email').value;

  const url = isReg ? '/auth/register' : '/auth/login';
  const body = isReg ? { username: u, email, password: p } : { username: u, password: p };

  try {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Authentication failed');

    token = data.access_token;
    user = data.user;
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    closeModal('auth-modal');
    updateUI();
    showToast(`Welcome @${user.username}`);
  } catch (err) {
    showToast(err.message);
  }
}

function logout() {
  token = null;
  user = null;
  localStorage.clear();
  updateUI();
  showToast('Logged out');
}

function openPostModal(id = '', title = '', content = '') {
  document.getElementById('post-id').value = id;
  document.getElementById('post-title').value = title;
  document.getElementById('post-content').value = content;
  document.getElementById('post-modal-title').textContent = id ? 'Edit Post' : 'Create Post';
  document.getElementById('post-modal').classList.add('active');
}

function editPost(id, title, content) {
  openPostModal(id, title, content);
}

async function savePost() {
  const id = document.getElementById('post-id').value;
  const title = document.getElementById('post-title').value;
  const content = document.getElementById('post-content').value;
  if (!title || !content) return showToast('Please enter title and content');

  const method = id ? 'PUT' : 'POST';
  const url = id ? `/posts/${id}` : '/posts';

  try {
    const res = await fetch(url, { method, headers: authHeaders(), body: JSON.stringify({ title, content }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error saving post');
    closeModal('post-modal');
    loadPosts();
    showToast('Post saved');
  } catch (err) {
    showToast(err.message);
  }
}

async function deletePost(id) {
  if (!confirm('Delete this post?')) return;
  try {
    const res = await fetch(`/posts/${id}`, { method: 'DELETE', headers: authHeaders() });
    if (!res.ok) throw new Error((await res.json()).detail || 'Error deleting');
    loadPosts();
    showToast('Post deleted');
  } catch (err) {
    showToast(err.message);
  }
}

async function openDetail(id) {
  currentPostId = id;
  try {
    const res = await fetch(`/posts/${id}`, { headers: authHeaders() });
    const p = await res.json();
    if (!res.ok) throw new Error(p.detail || 'Error loading post');

    document.getElementById('detail-title').textContent = p.title;
    document.getElementById('detail-author').textContent = p.author ? p.author.username : 'Unknown';
    document.getElementById('detail-date').textContent = new Date(p.created_at).toLocaleDateString();
    document.getElementById('detail-body').textContent = p.content;
    document.getElementById('detail-like-count').textContent = p.likes_count;

    renderComments(p.comments || []);
    document.getElementById('detail-modal').classList.add('active');
  } catch (err) {
    showToast(err.message);
  }
}

function renderComments(comments) {
  const list = document.getElementById('comments-list');
  list.innerHTML = comments.length ? comments.map(c => `
    <div class="comment-item">
      <div class="comment-header">
        <span>@${c.user ? escapeHtml(c.user.username) : 'User'}</span>
        <span>${new Date(c.created_at).toLocaleDateString()}</span>
      </div>
      <div>${escapeHtml(c.text)}</div>
    </div>
  `).join('') : '<p style="color:var(--text-muted);font-size:0.85rem">No comments yet.</p>';
}

async function addComment() {
  if (!token) return showToast('Please sign in to comment');
  const input = document.getElementById('comment-text');
  const text = input.value.trim();
  if (!text) return;

  try {
    const res = await fetch(`/posts/${currentPostId}/comments`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({ text }) });
    if (!res.ok) throw new Error((await res.json()).detail || 'Error commenting');
    input.value = '';
    openDetail(currentPostId);
    showToast('Comment added');
  } catch (err) {
    showToast(err.message);
  }
}

async function likePost(id) {
  if (!token) return showToast('Please sign in to like');
  try {
    const res = await fetch(`/posts/${id}/like`, { method: 'POST', headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error liking');
    loadPosts();
  } catch (err) {
    showToast(err.message);
  }
}

async function toggleDetailLike() {
  await likePost(currentPostId);
  openDetail(currentPostId);
}

function openAuthModal(mode) {
  switchAuthTab(mode);
  document.getElementById('auth-modal').classList.add('active');
}

function switchAuthTab(mode) {
  const isReg = mode === 'register';
  document.getElementById('auth-tab-login').classList.toggle('active', !isReg);
  document.getElementById('auth-tab-register').classList.toggle('active', isReg);
  document.getElementById('group-email').style.display = isReg ? 'block' : 'none';
  document.getElementById('auth-submit-btn').textContent = isReg ? 'Register' : 'Sign In';
}

function closeModal(id) {
  document.getElementById(id).classList.remove('active');
}

function escapeHtml(str) {
  return str ? str.replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m])) : '';
}

document.addEventListener('DOMContentLoaded', updateUI);
