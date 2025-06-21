document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('member-search');
  const hidden = document.getElementById('member_id');
  const list = document.getElementById('member-options');
  if (!input || !hidden || !list) return;

  input.addEventListener('change', () => {
    const match = Array.from(list.options).find(o => o.value === input.value);
    if (match) {
      hidden.value = match.dataset.id;
    }
  });
});
