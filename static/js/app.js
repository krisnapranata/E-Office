// Terapkan kelas Bootstrap ke field form Django dan konfirmasi aksi penting.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("#workspace form input, #workspace form select, #workspace form textarea").forEach((el) => {
    if (el.type === "hidden" || el.type === "submit") return;
    if (el.type === "checkbox") el.classList.add("form-check-input");
    else if (el.tagName === "SELECT") el.classList.add("form-select");
    else el.classList.add("form-control");
    if (el.closest("form.form-compact") && el.type !== "checkbox") {
      el.classList.add(el.tagName === "SELECT" ? "form-select-sm" : "form-control-sm");
    }
  });
  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("click", (ev) => { if (!confirm(el.dataset.confirm)) ev.preventDefault(); });
  });
});
