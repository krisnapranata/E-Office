/* Halaman login (disalin dari casemix): tampil/sembunyi password, validasi ringan, status "Memeriksa…"
 * + cegah kirim ganda, dan cadangan ikon bila gambar logo .le-logo-rs gagal dimuat. */
(function () {
    /* logo RS (merek kiri + kartu login) -> ikon bila /logo-rs/ 404 */
    document.querySelectorAll('img.le-logo-rs').forEach(function (logo) {
        function tanpaLogo() {
            var ikon = document.createElement('i');
            ikon.className = 'bi bi-hospital';
            ikon.setAttribute('aria-hidden', 'true');
            logo.replaceWith(ikon);
        }
        if (logo.complete && logo.naturalWidth === 0) { tanpaLogo(); }
        else { logo.addEventListener('error', tanpaLogo); }
    });

    var mata = document.getElementById('leMata'), sandi = document.getElementById('password'),
        user = document.getElementById('username'), form = document.getElementById('leForm'),
        tombol = document.getElementById('leTombol'), teks = tombol && tombol.querySelector('.le-tombol-teks');
    if (!form) { return; }

    mata.addEventListener('click', function () {
        var lihat = sandi.type === 'password';
        sandi.type = lihat ? 'text' : 'password';
        mata.setAttribute('aria-pressed', lihat ? 'true' : 'false');
        mata.setAttribute('aria-label', lihat ? 'Sembunyikan password' : 'Tampilkan password');
        mata.title = mata.getAttribute('aria-label');
        mata.querySelector('i').className = 'bi ' + (lihat ? 'bi-eye-slash' : 'bi-eye');
        sandi.focus();
    });
    [user, sandi].forEach(function (el) {
        el.addEventListener('input', function () { el.removeAttribute('aria-invalid'); });
    });
    form.addEventListener('submit', function (e) {
        if (!user.value.trim()) { e.preventDefault(); user.setAttribute('aria-invalid', 'true'); user.focus(); return; }
        if (!sandi.value) { e.preventDefault(); sandi.setAttribute('aria-invalid', 'true'); sandi.focus(); return; }
        if (tombol.getAttribute('aria-busy') === 'true') { e.preventDefault(); return; }   // cegah klik ganda
        sandi.type = 'password';                                                           // jangan tinggal terlihat
        tombol.setAttribute('aria-busy', 'true');
        teks.textContent = 'Memeriksa…';
    });
    // Kembali lewat tombol Back (bfcache): tombol normal lagi.
    window.addEventListener('pageshow', function () {
        tombol.removeAttribute('aria-busy');
        teks.textContent = 'Masuk ke E-Office';
    });
})();
