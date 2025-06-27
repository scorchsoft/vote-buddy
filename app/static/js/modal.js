function initModals() {
  document.querySelectorAll('[data-modal-target]').forEach(link => {
    const id = link.getAttribute('data-modal-target');
    const modal = document.getElementById(id);
    if (!modal) return;

    // Remove any existing listeners to avoid duplicates on htmx swaps
    const newLink = link.cloneNode(true);
    link.parentNode.replaceChild(newLink, link);

    newLink.addEventListener('click', e => {
      e.preventDefault();
      modal.showModal();
    });

    modal.querySelectorAll('[data-close-modal]').forEach(btn => {
      const newBtn = btn.cloneNode(true);
      btn.parentNode.replaceChild(newBtn, btn);
      newBtn.addEventListener('click', () => modal.close());
    });
  });
}

document.addEventListener('DOMContentLoaded', initModals);
document.body.addEventListener('htmx:load', initModals);
