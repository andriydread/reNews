// DOM Elements
const feedForm = document.getElementById("feedForm");
const feedTitle = document.getElementById("feedTitle");
const feedUrl = document.getElementById("feedUrl");
const submitBtn = document.getElementById("submitBtn");
const feedList = document.getElementById("feedList");
const alertBox = document.getElementById("alertBox");
const loadingFeeds = document.getElementById("loadingFeeds");

// Session-aware fetch: the access token dies after 60 min. On a 401, try one
// token refresh (rotates the refresh cookie server-side) and retry; if the
// refresh is also rejected the session is truly over — back to login.
async function apiFetch(url, options = {}) {
  let response = await fetch(url, options);
  if (response.status !== 401) return response;

  const refreshed = await fetch("/api/auth/refresh", { method: "POST" });
  if (!refreshed.ok) {
    window.location.href = "/login";
    // unreachable after redirect, but keeps callers' error handling sane
    return response;
  }
  return fetch(url, options);
}

// Static markup only — never interpolate data into this
const TRASH_ICON_SVG =
  '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>';

// Build one feed row with DOM APIs: feed data goes in via textContent, so it
// is never parsed as HTML.
function buildFeedRow(feed) {
  const li = document.createElement("li");
  li.className = "py-3 flex justify-between items-center"; // Make it a flex row

  const info = document.createElement("div");
  info.className = "flex flex-col overflow-hidden";

  const title = document.createElement("span");
  title.className = "font-bold text-gray-800";
  title.textContent = feed.title;

  const url = document.createElement("span");
  url.className = "text-sm text-gray-500 truncate";
  url.title = feed.url;
  url.textContent = feed.url;

  info.append(title, url);

  const del = document.createElement("button");
  del.className =
    "ml-4 text-red-500 hover:text-red-700 hover:bg-red-50 p-2 rounded transition";
  del.innerHTML = TRASH_ICON_SVG;
  del.addEventListener("click", () => deleteFeed(feed.id));

  li.append(info, del);
  return li;
}

// Utility function to show success/error messages
function showAlert(message, isError = false) {
  alertBox.textContent = message;
  alertBox.className = `mb-4 px-4 py-3 rounded relative text-sm ${isError ? "bg-red-100 text-red-700 border border-red-200" : "bg-green-100 text-green-700 border border-green-200"}`;
  alertBox.classList.remove("hidden");

  // Auto-hide after 5 seconds
  setTimeout(() => {
    alertBox.classList.add("hidden");
  }, 5000);
}

// 1. Fetch and Display Existing Feeds
async function loadFeeds() {
  feedList.innerHTML = "";
  loadingFeeds.classList.remove("hidden");

  try {
    const response = await apiFetch("/api/feeds");
    const feeds = await response.json();

    loadingFeeds.classList.add("hidden");

    if (feeds.length === 0) {
      feedList.innerHTML =
        '<li class="py-4 text-gray-500 text-sm">No feeds tracked yet.</li>';
      return;
    }

    feeds.forEach((feed) => feedList.appendChild(buildFeedRow(feed)));
  } catch (error) {
    loadingFeeds.classList.add("hidden");
    feedList.innerHTML =
      '<li class="py-4 text-red-500 text-sm">Failed to load feeds.</li>';
  }
}

// Function to delete a feed
async function deleteFeed(feedId) {
  // Confirm before deleting so you don't do it accidentally!
  if (
    !confirm("Are you sure? This will also delete all articles from this feed!")
  )
    return;

  try {
    const response = await apiFetch(`/api/feeds/${feedId}`, {
      method: "DELETE",
      credentials: "same-origin",
    });

    if (!response.ok) throw new Error("Failed to delete feed");

    showAlert("Feed deleted successfully!");
    loadFeeds(); // Reload the list
  } catch (error) {
    showAlert(error.message, true);
  }
}

// 2. Handle Form Submission
feedForm.addEventListener("submit", async (e) => {
  e.preventDefault(); // Stop the page from reloading

  // Disable button to prevent double-clicks
  submitBtn.disabled = true;
  submitBtn.innerHTML =
    '<div class="loader ease-linear rounded-full border-2 border-t-2 border-white h-5 w-5"></div>';

  const payload = {
    title: feedTitle.value.trim(),
    url: feedUrl.value.trim(),
  };

  try {
    // Because the page is protected by Basic Auth, the browser automatically
    // includes the correct Username/Password headers in this fetch request!
    const response = await apiFetch("/api/feeds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to add feed");
    }

    // Success!
    showAlert(`Successfully added ${payload.title}!`);
    feedTitle.value = "";
    feedUrl.value = "";

    // Reload the list to show the new feed
    loadFeeds();
  } catch (error) {
    showAlert(error.message, true);
  } finally {
    // Reset button
    submitBtn.disabled = false;
    submitBtn.innerHTML = "<span>Add Feed</span>";
  }
});

// Start
loadFeeds();
