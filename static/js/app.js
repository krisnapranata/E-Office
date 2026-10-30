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
  document.querySelectorAll("[data-org-toggle]").forEach((el) => el.addEventListener("click", () => {
    document.querySelectorAll(".org-node > details").forEach((d) => { d.open = el.dataset.orgToggle === "open"; });
  }));
  // Form pengguna: jabatan/peran/atasan disarankan dari Master Organisasi; isian yang diubah manual tidak ditimpa.
  const formPengguna = document.querySelector("[data-pengguna-form]");
  const dataSaran = document.getElementById("saran-unit");
  if (formPengguna && dataSaran) {
    const saran = JSON.parse(dataSaran.textContent);
    const f = (n) => formPengguna.querySelector(`[name="${n}"]`);
    const info = document.getElementById("saran-info");
    const otomatis = {};
    const esc = (t) => String(t).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
    const isi = (el, nilai) => {
      if (!el) return;
      const kini = el.value;
      if (kini === "" || kini === otomatis[el.name]) { el.value = nilai; otomatis[el.name] = el.value; }
    };
    const terapkan = () => {
      const s = saran[f("unit").value];
      if (!s) { info.hidden = true; return; }
      const kepala = f("kepala").checked;
      const x = kepala ? s.kepala : s.staf;
      isi(f("position"), x.jabatan);
      isi(f("role"), x.peran);
      isi(f("supervisor"), String(x.atasan));
      const baris = [`Atasan langsung disarankan: <b>${esc(x.atasan_nama || "– (belum ada kepala unit di atasnya)")}</b>.`];
      if (kepala && s.kepala_kini) baris.push(`Kepala unit saat ini: <b>${esc(s.kepala_kini)}</b> — akan digantikan.`);
      else if (!kepala && !s.kepala_kini) baris.push("Unit ini belum punya kepala; centang <i>Kepala/pimpinan unit ini</i> bila orang ini kepalanya.");
      info.innerHTML = baris.join(" ");
      info.hidden = false;
    };
    // Isian awal dari server (mode ubah) dianggap otomatis hanya bila kosong.
    ["position", "role", "supervisor"].forEach((n) => { if (f(n) && f(n).value === "") otomatis[n] = ""; });
    if (!formPengguna.querySelector('[name="first_name"]').value) otomatis.role = f("role").value;
    f("unit").addEventListener("change", terapkan);
    f("kepala").addEventListener("change", terapkan);
    if (f("unit").value) terapkan();
  }
  document.querySelectorAll("[data-print]").forEach((el) => el.addEventListener("click", () => window.print()));
  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("click", (ev) => { if (!confirm(el.dataset.confirm)) ev.preventDefault(); });
  });
});
