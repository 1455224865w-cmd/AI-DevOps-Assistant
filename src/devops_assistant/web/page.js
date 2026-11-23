document.getElementById("diagnose").addEventListener("click", () => run(() => api("/api/diagnoses", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    log: document.getElementById("log").value,
    provider: "github-actions",
    repository: document.getElementById("repository").value
  })
})));
document.getElementById("history").addEventListener("click", () => run(() => api("/api/diagnoses")));
document.getElementById("groups").addEventListener("click", () => run(() => api("/api/diagnoses/groups")));
document.getElementById("open").addEventListener("click", () => run(() => api("/api/diagnoses/" + encodeURIComponent(document.getElementById("item").value))));
