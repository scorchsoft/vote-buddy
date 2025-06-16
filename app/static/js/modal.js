document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-modal-target]').forEach(link => {
    const id = link.getAttribute('data-modal-target');
    const modal = document.getElementById(id);
    if (!modal) return;
    link.addEventListener('click', e => {
      e.preventDefault();
      modal.showModal();
    });
    modal.querySelectorAll('[data-close-modal]').forEach(btn => {
      btn.addEventListener('click', () => modal.close());
    });
  });
});
