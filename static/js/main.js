// static/js/main.js
let currentPage = 1;

// Only allow http(s) links from feeds
function safeUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol === "http:" || url.protocol === "https:") return url.href;
  } catch (e) {}
  return "#";
}

const cardTemplate = document.getElementById("articleCardTemplate");

// Clone the <template> and fill slots via textContent/href — untrusted feed
// data is never parsed as HTML, so escaping is structural, not a discipline.
function buildCard(article) {
  const card = cardTemplate.content.cloneNode(true);
  const link = safeUrl(article.link);

  card.querySelector('[data-slot="category"]').textContent = article.analysis
    ? article.analysis.category
    : "Uncategorized";

  const title = card.querySelector('[data-slot="title"]');
  title.textContent = article.title;
  title.href = link;

  card.querySelector('[data-slot="summary"]').textContent = article.analysis
    ? article.analysis.summary
    : "AI Analysis pending...";
  card.querySelector('[data-slot="date"]').textContent =
    "🗓 " + new Date(article.published_at).toLocaleDateString();
  card.querySelector('[data-slot="readmore"]').href = link;
  return card;
}

const grid = document.getElementById("articlesGrid");
const loading = document.getElementById("loadingState");
const empty = document.getElementById("emptyState");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const pageInfo = document.getElementById("pageInfo");
const catFilter = document.getElementById("categoryFilter");
const sizeFilter = document.getElementById("sizeFilter");

function loadMemory() {
  const savedCat = localStorage.getItem("reNews_category");
  const savedSize = localStorage.getItem("reNews_size");
  const savedPage = localStorage.getItem("reNews_page");

  if (savedCat) catFilter.value = savedCat;
  if (savedSize) sizeFilter.value = savedSize;
  if (savedPage) currentPage = parseInt(savedPage);
}

function saveMemory() {
  localStorage.setItem("reNews_category", catFilter.value);
  localStorage.setItem("reNews_size", sizeFilter.value);
  localStorage.setItem("reNews_page", currentPage);
}

async function fetchArticles() {
  grid.innerHTML = "";
  empty.classList.add("hidden");
  loading.classList.remove("hidden");
  saveMemory();

  let url = `/api/articles?page=${currentPage}&size=${sizeFilter.value}`;
  if (catFilter.value)
    url += `&category=${encodeURIComponent(catFilter.value)}`;

  try {
    const response = await fetch(url);
    const data = await response.json();

    loading.classList.add("hidden");

    if (data.items.length === 0) {
      // A stale page restored from localStorage (or a shrunken result set)
      // lands past the last page — snap back instead of showing "no articles"
      if (currentPage > 1 && data.total > 0) {
        currentPage = 1;
        fetchArticles();
        return;
      }
      empty.classList.remove("hidden");
      prevBtn.disabled = currentPage === 1;
      nextBtn.disabled = true;
      pageInfo.innerText = `Page ${currentPage} of 0`;
      return;
    }

    const fragment = document.createDocumentFragment();
    data.items.forEach((article) => fragment.appendChild(buildCard(article)));
    grid.appendChild(fragment);

    // Calculate total pages (e.g., 27 items / 10 per page = 3 pages)
    const totalPages = Math.ceil(data.total / parseInt(sizeFilter.value)) || 1;

    // Format: Page 3 / 3 (27 Total Articles)
    pageInfo.innerText = `Page ${currentPage} / ${totalPages} (${data.total} Total Articles)`;

    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = data.items.length < parseInt(sizeFilter.value);
  } catch (error) {
    console.error("Failed to fetch articles", error);
    loading.classList.add("hidden");
    grid.innerHTML =
      '<p class="text-red-500 text-center py-10 w-full">Error loading database.</p>';
  }
}

// Event Listeners
catFilter.addEventListener("change", () => {
  currentPage = 1;
  fetchArticles();
});
sizeFilter.addEventListener("change", () => {
  currentPage = 1;
  fetchArticles();
});
prevBtn.addEventListener("click", () => {
  if (currentPage > 1) {
    currentPage--;
    fetchArticles();
  }
});
nextBtn.addEventListener("click", () => {
  currentPage++;
  fetchArticles();
});

document.getElementById("resetFiltersBtn").addEventListener("click", () => {
  catFilter.value = "";
  currentPage = 1;
  fetchArticles();
});

// Start
loadMemory();
fetchArticles();
