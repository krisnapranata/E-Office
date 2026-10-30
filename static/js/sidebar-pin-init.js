/* Dimuat SINKRON di awal <body>: terapkan status pin sidebar sebelum sidebar dirender (tanpa kedip).
   Bawaan: menu SELALU terbuka (ikon + tulisan) agar mudah dipahami; ramping hanya bila pengguna memilihnya. */
try { if (localStorage.getItem('eoffice-sidebar-pinned') !== '0') document.body.classList.add('sidebar-pinned'); }
catch (e) { document.body.classList.add('sidebar-pinned'); /* mode privat */ }
