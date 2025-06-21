document.addEventListener('DOMContentLoaded', () => {
  function formatRemaining(diff) {
    if (diff <= 0) return 'Closed';
    const hours = diff / 3600000;
    if (hours >= 24) {
      const days = Math.ceil(hours / 24);
      return `${days} day${days !== 1 ? 's' : ''}`;
    }
    const h = Math.ceil(hours);
    return `${h} hour${h !== 1 ? 's' : ''}`;
  }

  document.querySelectorAll('[data-progress-open]').forEach(progress => {
    const bar = progress.querySelector('.bp-progress-bar');
    const open = new Date(progress.dataset.progressOpen);
    const close = new Date(progress.dataset.progressClose);
    const info = document.getElementById(`${progress.id}-info`);
    const pctText = document.getElementById(`${progress.id}-percent-text`);
    const countdown = document.getElementById(`${progress.id}-countdown`);

    function update() {
      const now = new Date();
      const total = close - open;
      let pct = 0;
      if (total > 0) {
        pct = ((now - open) / total) * 100;
      }
      pct = Math.max(0, Math.min(100, pct));
      if (bar) bar.style.width = `${pct}%`;
      progress.setAttribute('aria-valuenow', Math.round(pct));
      if (pctText) pctText.textContent = Math.round(pct);
      if (countdown) countdown.textContent = formatRemaining(close - now);
      if (info) info.dataset.remaining = countdown ? countdown.textContent : '';
    }

    update();
    setInterval(update, 60000);
  });
});
