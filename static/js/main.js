// static/js/main.js
let currentPage = 1;

const grid = document.getElementById("articlesGrid");
const loading = document.getElementById("loadingState");
const empty = document.getElementById("emptyState");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const pageInfo = document.getElementById("pageInfo");
const catFilter = document.getElementById("categoryFilter");
const scoreFilter = document.getElementById("scoreFilter");
const sizeFilter = document.getElementById("sizeFilter");

function loadMemory() {
  const savedCat = localStorage.getItem("reNews_category");
  const savedScore = localStorage.getItem("reNews_score");
  const savedSize = localStorage.getItem("reNews_size");
  const savedPage = localStorage.getItem("reNews_page");

  if (savedCat) catFilter.value = savedCat;
  if (savedScore) scoreFilter.value = savedScore;
  if (savedSize) sizeFilter.value = savedSize;
  if (savedPage) currentPage = parseInt(savedPage);
}

function saveMemory() {
  localStorage.setItem("reNews_category", catFilter.value);
  localStorage.setItem("reNews_score", scoreFilter.value);
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
  if (scoreFilter.value) url += `&min_score=${scoreFilter.value}`;

  try {
    const response = await fetch(url);
    const data = await response.json();

    loading.classList.add("hidden");

    if (data.items.length === 0) {
      empty.classList.remove("hidden");
      prevBtn.disabled = currentPage === 1;
      nextBtn.disabled = true;
      pageInfo.innerText = `Page ${currentPage} of 0`;
      return;
    }

    data.items.forEach((article) => {
      const summary = article.analysis
        ? article.analysis.summary
        : "AI Analysis pending...";
      const score = article.analysis ? article.analysis.score : "?";
      const category = article.analysis
        ? article.analysis.category
        : "Uncategorized";
      const date = new Date(article.published_at).toLocaleDateString();

      const card = `
                <div class="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition border border-gray-100 flex flex-col">
                    <div class="p-5 flex-grow">
                        <div class="flex justify-between items-start mb-3">
                            <span class="text-xs font-semibold bg-blue-100 text-blue-800 px-2 py-1 rounded">${category}</span>
                            <span class="text-sm font-bold ${score >= 8 ? "text-green-600" : "text-gray-500"}">🔥 ${score}/10</span>
                        </div>
                        <a href="${article.link}" target="_blank" class="block mt-1 text-lg font-bold text-gray-900 hover:text-blue-600 leading-tight mb-2">
                            ${article.title}
                        </a>
                        <p class="text-gray-600 text-sm line-clamp-4">${summary}</p>
                    </div>
                    <div class="bg-gray-50 px-5 py-3 border-t border-gray-100 text-xs text-gray-500 flex justify-between">
                        <span>🗓 ${date}</span>
                        <a href="${article.link}" target="_blank" class="text-blue-600 font-medium hover:underline">Read full article &rarr;</a>
                    </div>
                </div>
            `;
      grid.innerHTML += card;
    });

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
scoreFilter.addEventListener("change", () => {
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

// Attach to window so the HTML button can call it
window.resetFilters = function () {
  catFilter.value = "";
  scoreFilter.value = "";
  currentPage = 1;
  fetchArticles();
};

// Start
loadMemory();
fetchArticles();
