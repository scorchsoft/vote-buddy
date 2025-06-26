function initMarkdownEditors() {
  if (typeof EasyMDE === 'undefined') {
    console.error('EasyMDE not loaded');
    return;
  }

  document.querySelectorAll('textarea[data-markdown-editor]').forEach((area) => {
    new EasyMDE({
      element: area,
      spellChecker: false,
      forceSync: true,
      autoDownloadFontAwesome: false,
    });
  });
}

if (document.readyState !== 'loading') {
  initMarkdownEditors();
} else {
  document.addEventListener('DOMContentLoaded', initMarkdownEditors);
}
