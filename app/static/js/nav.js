document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('nav-toggle');
  const drawer = document.getElementById('nav-drawer');
  let keyHandler;

  function closeDrawer() {
    drawer.classList.remove('open');
    drawer.setAttribute('hidden', '');
    toggle.setAttribute('aria-expanded', 'false');
    if (keyHandler) {
      document.removeEventListener('keydown', keyHandler);
      keyHandler = null;
    }
  }

  function openDrawer() {
    drawer.removeAttribute('hidden');
    requestAnimationFrame(() => drawer.classList.add('open'));
    toggle.setAttribute('aria-expanded', 'true');
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
  const themeIcon = document.getElementById('theme-icon');
  const root = document.documentElement;

  function updateThemeUI(theme) {
    if (themeIcon) {
      themeIcon.src =
        theme === 'dark' ? themeIcon.dataset.sun : themeIcon.dataset.moon;
    }
    themeBtn.setAttribute(
      'aria-label',
      theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
    );
  }

  if (themeBtn) {
    const saved = localStorage.getItem('theme');
    if (saved) {
      root.dataset.theme = saved;
      updateThemeUI(saved);
    } else {
      updateThemeUI(root.dataset.theme || 'light');
    }

    themeBtn.addEventListener('click', () => {
      const newTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
      root.dataset.theme = newTheme;
      localStorage.setItem('theme', newTheme);
      updateThemeUI(newTheme);
    });
  }
});
