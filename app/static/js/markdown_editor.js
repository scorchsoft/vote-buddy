
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('textarea[data-markdown-editor]').forEach(area => {
    const wrapper = document.createElement('div');
    wrapper.className = 'space-y-2';
    area.parentNode.insertBefore(wrapper, area);
    wrapper.appendChild(area);

    const buttons = document.createElement('div');
    buttons.className = 'flex gap-2';
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.textContent = 'Edit';
    editBtn.className = 'bp-btn-secondary';
    const previewBtn = document.createElement('button');
    previewBtn.type = 'button';
    previewBtn.textContent = 'Preview';
    previewBtn.className = 'bp-btn-secondary';
    buttons.appendChild(editBtn);
    buttons.appendChild(previewBtn);
    wrapper.insertBefore(buttons, area);

    const preview = document.createElement('div');
    preview.className = 'bp-card p-3 hidden';
    wrapper.appendChild(preview);

    let previewMode = false;
    const toggle = (mode) => {
      previewMode = mode !== undefined ? mode : !previewMode;
      if (previewMode) {
        const html = DOMPurify.sanitize(marked.parse(area.value));
        preview.innerHTML = html;
        area.classList.add('hidden');
        preview.classList.remove('hidden');
      } else {
        area.classList.remove('hidden');
        preview.classList.add('hidden');
      }
    };

    editBtn.addEventListener('click', () => toggle(false));
    previewBtn.addEventListener('click', () => toggle(true));
  });
});

