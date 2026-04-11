// static/theme.js
// Dark/Light mode toggle

document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('theme-toggle-btn');
    const icon = document.getElementById('theme-icon');
    const darkClass = 'dark-mode';
    const storageKey = 'theme-mode';

    // Set initial mode from localStorage
    if (localStorage.getItem(storageKey) === 'dark') {
        document.body.classList.add(darkClass);
        if (icon) icon.classList.remove('fa-moon');
        if (icon) icon.classList.add('fa-sun');
    }

    btn && btn.addEventListener('click', function () {
        document.body.classList.toggle(darkClass);
        const isDark = document.body.classList.contains(darkClass);
        if (icon) {
            icon.classList.toggle('fa-moon', !isDark);
            icon.classList.toggle('fa-sun', isDark);
        }
        localStorage.setItem(storageKey, isDark ? 'dark' : 'light');
    });
});
