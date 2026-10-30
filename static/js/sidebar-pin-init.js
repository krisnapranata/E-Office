/* Dimuat SINKRON di awal <body>: terapkan status pin sidebar sebelum sidebar dirender (tanpa kedip). */
try { if (localStorage.getItem('eoffice-sidebar-pinned') === '1') document.body.classList.add('sidebar-pinned'); } catch (e) { /* mode privat */ }
