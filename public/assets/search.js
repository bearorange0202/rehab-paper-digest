async function bootSearch() {
  const input = document.querySelector('#searchInput');
  const results = document.querySelector('#searchResults');
  if (!input || !results) return;
  const original = results.innerHTML;
  let items = [];
  try {
    const base = document.querySelector('meta[name="site-base-path"]')?.content || '';
    const response = await fetch(`${base}/search.json`);
    items = await response.json();
  } catch {
    return;
  }
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) {
      results.innerHTML = original;
      return;
    }
    const matched = items.filter((item) => {
      const haystack = [item.title, item.summary, item.pmid, item.doi, ...(item.categories || [])].join(' ').toLowerCase();
      return haystack.includes(q);
    }).slice(0, 30);
    results.innerHTML = matched.length ? matched.map((item) => `
      <article class="article-card">
        <div class="meta-line">${escapeHtml(item.published_date || '')}</div>
        <h2><a href="${escapeAttr(item.url)}">${escapeHtml(item.title)}</a></h2>
        <p>${escapeHtml(item.summary || '')}</p>
        <div class="tags">${(item.categories || []).map((c) => `<span class="tag">${escapeHtml(c)}</span>`).join('')}</div>
      </article>
    `).join('') : '<p class="empty">該当する記事はありません。</p>';
  });
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, '&#96;');
}
bootSearch();
