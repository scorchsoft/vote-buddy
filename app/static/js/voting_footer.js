document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('vote-form');
  const footer = document.getElementById('vote-footer');
  const summary = document.getElementById('vote-summary');
  if (!form || !footer || !summary) return;

  const inputs = Array.from(form.querySelectorAll('input[type="radio"]'));
  const names = [...new Set(inputs.map(i => i.name))];
  function update() {
    const filled = names.filter(n => form.querySelector(`input[name="${n}"]:checked`)).length;
    summary.textContent = `${filled} of ${names.length} selected`;
    footer.classList.remove('hidden');
  }
  inputs.forEach(i => i.addEventListener('change', update));
  update();
});
