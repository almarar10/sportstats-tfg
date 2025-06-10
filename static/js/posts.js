/* ---------------------------------------------------------------------------
   Helper para llamadas AJAX a tu API
--------------------------------------------------------------------------- */
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

/* ---------------------------------------------------------------------------
   Variables para paginación, pestañas y usuario
--------------------------------------------------------------------------- */
let cursor = null;                       // ISO string de la última fecha cargada
let currentTab = 'all';                  // 'all' o 'for-you'
const CURRENT_USER = window.CURRENT_USER || ""; 

// ---------------------------------------------------------------------------
// NUEVO: Set para almacenar IDs de recomendaciones que ya hemos pintado.
// De esta forma evitamos mostrar dos veces el mismo post en "Para ti".
// ---------------------------------------------------------------------------
const seenRecommendations = new Set();

/* ---------------------------------------------------------------------------
   Carga inicial y paginada de posts según pestaña activa
--------------------------------------------------------------------------- */
async function loadPosts() {
  // Construimos los parámetros de consulta
  const params = new URLSearchParams();
  params.set('limit', 10);
  if (cursor) params.set('cursor', cursor);

  // Elegimos endpoint en función de la pestaña
  const base = currentTab === 'for-you'
    ? '/api/recommendations'   // NO soporta paginación formal, de momento
    : '/api/posts';

  // Llamada
  const result = await api(`${base}?${params.toString()}`);
  // En /api/posts la respuesta es { posts: [...] }
  // En /api/recommendations la respuesta es { posts: [...] }
  const posts = result.posts || [];

  if (currentTab === 'for-you') {
    // ------------------------------------------------------------------------
    // Para la pestaña "Para ti", filtramos duplicados comparando con seenRecommendations
    // ------------------------------------------------------------------------
    let anyNew = false;
    posts.forEach(p => {
      if (!seenRecommendations.has(p.id)) {
        renderPost(p);
        seenRecommendations.add(p.id);
        anyNew = true;
      }
    });
    // Si NO había ningún post nuevo (todos los IDs ya estaban en el Set),
    // deshabilitamos el botón "Cargar más".
    if (!anyNew) {
      document.getElementById('load-more').disabled = true;
    }
  } else {
    // ------------------------------------------------------------------------
    // Pestaña "Todos": igual que antes, pintamos todos los posts venideros
    // ------------------------------------------------------------------------
    if (posts.length === 0) {
      document.getElementById('load-more').disabled = true;
      return;
    }
    posts.forEach(renderPost);
  }

  // Avanzamos cursor al created_at del último elemento de la respuesta,
  // para que en "Todos" obtengamos los siguientes posts. En "Para ti"
  // no tiene efecto práctico (pero lo dejamos para que no rompa).
  if (posts.length > 0) {
    const last = posts[posts.length - 1];
    cursor = last.created_at;
  }
}

/* ---------------------------------------------------------------------------
   Render de un solo post
--------------------------------------------------------------------------- */
function renderPost(p) {
  const container = document.getElementById('posts-container');
  const card = document.createElement('div');
  card.className = 'post-card';

  // ---------------- Header ----------------
  const header = document.createElement('header');
  header.className = 'post-header';
  header.innerHTML = `
    <div class="user-ident">
      <span class="sport-emoji">${["⚽","🏀","🏃","🏁","🥊"][p.fav_sport] || "❓"}</span>
      <span class="user-handle">@${p.author}</span>
    </div>
    <time class="post-time">
      ${new Date(p.edited && p.updated_at ? p.updated_at : p.created_at)
         .toLocaleString()}
    </time>
  `;
  card.append(header);

  // ---------------- Content ----------------
  const body = document.createElement('div');
  body.className = 'post-content';
  body.textContent = p.content;
  card.append(body);

  // ---------------- Footer ----------------
  const footer = document.createElement('footer');
  footer.className = 'post-footer';

  // Like button
  const likeBtn = document.createElement('button');
  likeBtn.className = `like-btn ${p.liked ? 'liked' : ''}`;
  likeBtn.dataset.id = p.id;
  likeBtn.innerHTML = `
    <span class="heart">${p.liked ? '❤' : '♡'}</span>
    <span class="likes-count">${p.likes}</span>
  `;
  likeBtn.onclick = toggleLike;
  footer.append(likeBtn);

  // Si es tu propio post: editar + borrar
  if (p.author === CURRENT_USER) {
    const actions = document.createElement('div');
    actions.className = 'actions';
    const edit = document.createElement('button');
    edit.className = 'edit-btn';
    edit.textContent = '✎';
    edit.dataset.id = p.id;
    edit.onclick = startEditPost;
    const del = document.createElement('button');
    del.className = 'delete-btn';
    del.textContent = '🗑️';
    del.dataset.id = p.id;
    del.onclick = deletePost;
    actions.append(edit, del);
    footer.append(actions);
  }

  card.append(footer);

  // ---------------- Edited label ----------------
  if (p.edited) {
    const label = document.createElement('div');
    label.className = 'edited-label';
    label.innerHTML = '<em>Este post ha sido editado</em>';
    card.append(label);
  }

  container.append(card);
}

/* ---------------------------------------------------------------------------
   Toggle Like: POST /api/posts/:id/like
--------------------------------------------------------------------------- */
async function toggleLike(e) {
  const btn = e.currentTarget;
  const postId = btn.dataset.id;
  try {
    const { liked, likes } = await api(`/api/posts/${postId}/like`, {
      method: 'POST'
    });
    btn.classList.toggle('liked', liked);
    btn.querySelector('.likes-count').textContent = likes;
  } catch (err) {
    console.error("Error al dar like:", err);
  }
}

/* ---------------------------------------------------------------------------
   Comenzar edición inline de un post propio
--------------------------------------------------------------------------- */
function startEditPost(e) {
  const postId = e.currentTarget.dataset.id;
  const card   = e.currentTarget.closest('.post-card');
  const bodyDiv = card.querySelector('.post-content');

  // 1) Reemplaza el div por un textarea
  const textarea = document.createElement('textarea');
  textarea.className = 'edit-textarea';
  textarea.value       = bodyDiv.textContent;
  textarea.rows        = 3;
  textarea.style.width = '100%';
  card.replaceChild(textarea, bodyDiv);

  // 2) Oculta editar/borrar y añade Guardar/Cancelar
  const editBtn   = card.querySelector('.edit-btn');
  const deleteBtn = card.querySelector('.delete-btn');
  const footer    = card.querySelector('.post-footer');
  editBtn.style.display   = 'none';
  deleteBtn.style.display = 'none';

  const saveBtn = document.createElement('button');
  saveBtn.textContent = 'Guardar';
  saveBtn.className   = 'btn-primary save-edit-btn';
  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = 'Cancelar';
  cancelBtn.className   = 'btn-secondary cancel-edit-btn';
  footer.append(saveBtn, cancelBtn);

  // 3) Handlers Guardar / Cancelar
  saveBtn.onclick = async () => {
    const newContent = textarea.value.trim();
    if (!newContent) return alert("El post no puede quedar vacío");
    try {
      await api(`/api/posts/${postId}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ content: newContent })
      });
      resetFeed();
    } catch (err) {
      console.error("Error guardando edición:", err);
    }
  };
  cancelBtn.onclick = () => resetFeed();
}

/* ---------------------------------------------------------------------------
   Borrar un post propio
--------------------------------------------------------------------------- */
async function deletePost(e) {
  if (!confirm("¿Seguro que quieres borrar este post?")) return;
  const postId = e.currentTarget.dataset.id;
  try {
    await api(`/api/posts/${postId}`, { method: 'DELETE' });
    resetFeed();
  } catch (err) {
    console.error("Error borrando post:", err);
  }
}

/* ---------------------------------------------------------------------------
   Resetear y recargar todo el feed
--------------------------------------------------------------------------- */
function resetFeed() {
  cursor = null;
  const container = document.getElementById('posts-container');
  container.innerHTML = '';
  document.getElementById('load-more').disabled = false;
  // También limpiamos el set de recomendaciones para “Para ti”
  if (currentTab === 'for-you') {
    seenRecommendations.clear();
  }
  loadPosts();
}

/* ---------------------------------------------------------------------------
   Cambio de pestaña (Todos / Para ti)
--------------------------------------------------------------------------- */
function switchTab(tab) {
  if (tab === currentTab) return;
  currentTab = tab;
  document.querySelectorAll('.posts-tabs .tab')
          .forEach(btn => btn.classList.toggle('active', btn.id === 'tab-' + tab));
  resetFeed();
}

/* ---------------------------------------------------------------------------
   Inicialización al cargar la página
--------------------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  // Pestañas
  document.getElementById('tab-all').onclick     = () => switchTab('all');
  document.getElementById('tab-for-you').onclick = () => switchTab('for-you');

  // Cargar más
  document.getElementById('load-more').onclick   = loadPosts;

  // Postear
  document.getElementById('submit-post').onclick = async () => {
    const textarea = document.getElementById('post-content');
    const content  = textarea.value.trim();
    if (!content) return;
    try {
      await api('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      textarea.value = '';
      resetFeed();
    } catch (err) {
      console.error("Error publicando post:", err);
    }
  };

  // Primera carga
  loadPosts();
});
