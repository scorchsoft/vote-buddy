document.addEventListener('DOMContentLoaded', () => {
  function setup(btnId, containerId) {
    const btn = document.getElementById(btnId);
    const container = document.getElementById(containerId);
    if (!btn || !container) return;
    btn.addEventListener('click', () => {
      const open = btn.dataset.state === 'open';
      container.querySelectorAll('details').forEach(d => d.open = !open);
      btn.dataset.state = open ? 'closed' : 'open';
      btn.textContent = open ? 'Expand all' : 'Collapse all';
    });
  }
  setup('toggle-amendments', 'amendments-list');
  setup('toggle-motions', 'motions-list');
});
