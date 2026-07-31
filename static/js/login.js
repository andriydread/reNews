// Login form handler — lives in a file (not inline) so the CSP can stay
// script-src 'self' with no unsafe-inline.
document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("loginBtn");
  const errorBox = document.getElementById("errorBox");
  btn.disabled = true;
  btn.textContent = "Verifying...";

  const formData = new FormData();
  formData.append("username", document.getElementById("username").value);
  formData.append("password", document.getElementById("password").value);

  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      // Cookie is automatically saved by the browser!
      window.location.href = "/admin";
    } else {
      const data = await response.json();
      errorBox.textContent = data.detail || "Login failed";
      errorBox.classList.remove("hidden");
      btn.disabled = false;
      btn.textContent = "Login";
    }
  } catch (err) {
    errorBox.textContent = "Network error";
    errorBox.classList.remove("hidden");
    btn.disabled = false;
    btn.textContent = "Login";
  }
});
