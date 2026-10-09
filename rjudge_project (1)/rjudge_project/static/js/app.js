// Small helpers shared by all pages.
// Toasts disappear after a few seconds.
document.querySelectorAll(".toast").forEach(t => setTimeout(() => t.remove(), 3500));

// Dashboard progress ring animates to the solved percentage.
const fg = document.getElementById("fg");
if (fg) {
  const circumference = parseFloat(fg.getAttribute("stroke-dasharray"));
  requestAnimationFrame(() => setTimeout(() => {
    fg.style.strokeDashoffset = circumference * (1 - parseFloat(fg.dataset.pct) / 100);
  }, 60));
}

// Submit button shows a spinner while the server judges the code.
const form = document.getElementById("submitForm");
if (form) {
  form.addEventListener("submit", () => {
    const b = form.querySelector("button");
    b.classList.add("busy");
    b.textContent = "Judging...";
    setTimeout(() => (b.disabled = true), 0);
  });
}

// Search box on the problems page.
const q = document.getElementById("q");
if (q) {
  q.addEventListener("input", () => {
    const t = q.value.toLowerCase();
    document.querySelectorAll("#plist .pi").forEach(a => {
      a.style.display = a.textContent.toLowerCase().includes(t) ? "" : "none";
    });
  });
}
