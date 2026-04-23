// theme.js — Dark/Light mavzusi (data-theme attribute orqali)
(function () {
  const STORAGE_KEY = 'theme-mode';
  const DARK = 'dark', LIGHT = 'light';

  function setTheme(mode) {
    document.documentElement.setAttribute('data-theme', mode);
    localStorage.setItem(STORAGE_KEY, mode);
    const icon = document.getElementById('theme-icon');
    if (icon) {
      icon.classList.toggle('fa-moon', mode === LIGHT);
      icon.classList.toggle('fa-sun', mode === DARK);
    }
  }

  // Boshlang'ich rejimni qo'llash
  const saved = localStorage.getItem(STORAGE_KEY) || LIGHT;
  setTheme(saved);

  document.addEventListener('DOMContentLoaded', function () {
    setTheme(localStorage.getItem(STORAGE_KEY) || LIGHT);
    const btn = document.getElementById('theme-toggle-btn');
    btn && btn.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-theme') || LIGHT;
      setTheme(current === DARK ? LIGHT : DARK);
    });
  });
})();
