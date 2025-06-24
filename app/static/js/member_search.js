document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[data-member-target]').forEach(input => {
    const hidden = document.getElementById(input.dataset.memberTarget);
    const list = document.getElementById(input.getAttribute('list'));
    if (!hidden || !list) return;
    input.addEventListener('change', () => {
      const match = Array.from(list.options).find(o => o.value === input.value);
      if (match) {
        hidden.value = match.dataset.id;
      }
    });
  });
});
