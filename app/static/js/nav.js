document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('nav-toggle');
  const drawer = document.getElementById('nav-drawer');
  if (toggle && drawer) {
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      if (expanded) {
        drawer.classList.remove('open');
        drawer.setAttribute('hidden', '');
      } else {
        drawer.removeAttribute('hidden');
        requestAnimationFrame(() => drawer.classList.add('open'));
      }
    });
  }

  const themeBtn = document.getElementById('theme-toggle');
  const root = document.documentElement;
  if (themeBtn) {
    const saved = localStorage.getItem('theme');
    if (saved) root.dataset.theme = saved;
    themeBtn.addEventListener('click', () => {
      const newTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
      root.dataset.theme = newTheme;
      localStorage.setItem('theme', newTheme);
      themeBtn.setAttribute(
        'aria-label',
        newTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
      );
    });
  }
});
