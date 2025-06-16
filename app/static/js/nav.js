document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('nav-toggle');
  const drawer = document.getElementById('nav-drawer');
  if (!toggle || !drawer) return;
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
});
