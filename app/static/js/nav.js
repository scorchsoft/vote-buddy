document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('nav-toggle');
  const drawer = document.getElementById('nav-drawer');
  let keyHandler;

  function closeDrawer() {
    drawer.classList.remove('open');
    drawer.setAttribute('hidden', '');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML = '<span class="sr-only">Menu</span>&#9776;';
    if (keyHandler) {
      document.removeEventListener('keydown', keyHandler);
      keyHandler = null;
    }
  }

  function openDrawer() {
    drawer.removeAttribute('hidden');
    requestAnimationFrame(() => drawer.classList.add('open'));
    toggle.setAttribute('aria-expanded', 'true');
    toggle.innerHTML = '<span class="sr-only">Menu</span>&#10005;';
    keyHandler = e => {
      if (e.key === 'Escape') closeDrawer();
    };
    document.addEventListener('keydown', keyHandler);
  }

  if (toggle && drawer) {
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      expanded ? closeDrawer() : openDrawer();
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
