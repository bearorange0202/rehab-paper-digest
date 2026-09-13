function bootSearch() {
  const form = document.querySelector('.list-tools');
  const input = document.querySelector('#searchInput');
  const results = document.querySelector('#searchResults');
  const sort = document.querySelector('#sortSelect');
  if (!input || !results) return;
  const emptyHtml = '<p class="empty">該当する記事はありません。</p>';
  const originalCards = Array.from(results.querySelectorAll('.article-card')).map((card) => card.cloneNode(true));

  function applyFilters() {
    const q = input.value.trim().toLowerCase();
    const order = sort?.value || 'new';
    const cards = originalCards
      .filter((card) => !q || String(card.dataset.search || '').includes(q))
      .sort((a, b) => compareCards(a, b, order));

    results.replaceChildren();
    if (!cards.length) {
      results.innerHTML = emptyHtml;
      return;
    }
    cards.forEach((card) => results.appendChild(card.cloneNode(true)));
  }

  form?.addEventListener('submit', (event) => {
    event.preventDefault();
    applyFilters();
  });
  input.addEventListener('input', applyFilters);
  sort?.addEventListener('change', applyFilters);
  applyFilters();
}

function compareCards(a, b, order) {
  if (order === 'old') {
    return String(a.dataset.date || '').localeCompare(String(b.dataset.date || ''));
  }
  return String(b.dataset.date || '').localeCompare(String(a.dataset.date || ''));
}
function bootCategoryFilters() {
  document.querySelectorAll('[data-category-filter]').forEach((input) => {
    const section = input.closest('[data-category-filter-section]');
    if (!section) return;
    const form = input.closest('form');
    const links = Array.from(section.querySelectorAll('.tag-link'));
    function applyCategoryFilter() {
      const q = input.value.trim().toLowerCase();
      links.forEach((link) => {
        link.hidden = Boolean(q) && !link.textContent.toLowerCase().includes(q);
      });
    }
    form?.addEventListener('submit', (event) => {
      event.preventDefault();
      applyCategoryFilter();
    });
    input.addEventListener('input', applyCategoryFilter);
    applyCategoryFilter();
  });
}

bootSearch();
bootCategoryFilters();
