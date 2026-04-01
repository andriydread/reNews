// DOM Elements
const feedForm = document.getElementById("feedForm");
const feedTitle = document.getElementById("feedTitle");
const feedUrl = document.getElementById("feedUrl");
const submitBtn = document.getElementById("submitBtn");
const feedList = document.getElementById("feedList");
const alertBox = document.getElementById("alertBox");
const loadingFeeds = document.getElementById("loadingFeeds");

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
    const response = await fetch("/api/feeds");
    const feeds = await response.json();

    loadingFeeds.classList.add("hidden");

    if (feeds.length === 0) {
      feedList.innerHTML =
        '<li class="py-4 text-gray-500 text-sm">No feeds tracked yet.</li>';
      return;
    }

    feeds.forEach((feed) => {
      const li = document.createElement("li");
      li.className = "py-3 flex justify-between items-center"; // Make it a flex row
      li.innerHTML = `
        <div class="flex flex-col overflow-hidden">
            <span class="font-bold text-gray-800">${feed.title}</span>
            <span class="text-sm text-gray-500 truncate" title="${feed.url}">${feed.url}</span>
        </div>
        <button onclick="deleteFeed(${feed.id})" class="ml-4 text-red-500 hover:text-red-700 hover:bg-red-50 p-2 rounded transition">
            <!-- Trash Can SVG Icon -->
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
        </button>
    `;
      feedList.appendChild(li);
    });
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
    const response = await fetch(`/api/feeds/${feedId}`, {
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
    const response = await fetch("/api/feeds", {
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
