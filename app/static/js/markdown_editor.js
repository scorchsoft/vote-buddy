document.addEventListener('DOMContentLoaded', () => {
  // Check if required libraries are loaded
  if (typeof marked === 'undefined' || typeof DOMPurify === 'undefined') {
    console.error('Markdown editor: marked or DOMPurify library not loaded');
    return;
  }

  const textareas = document.querySelectorAll('textarea[data-markdown-editor]');
  console.log(`Found ${textareas.length} textareas with data-markdown-editor attribute`);
  
  textareas.forEach(area => {
    console.log('Initializing markdown editor for:', area.name || area.id);
    
    const wrapper = document.createElement('div');
    wrapper.className = 'space-y-2';
    area.parentNode.insertBefore(wrapper, area);
    wrapper.appendChild(area);

    const buttons = document.createElement('div');
    buttons.className = 'flex gap-2';
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.textContent = 'Edit';
    editBtn.className = 'px-4 py-1 text-sm font-medium rounded bg-bp-blue text-white hover:bg-bp-blue-light transition-colors'; // Active by default
    const previewBtn = document.createElement('button');
    previewBtn.type = 'button';
    previewBtn.textContent = 'Preview';
    previewBtn.className = 'px-4 py-1 text-sm font-medium rounded border-2 border-bp-blue text-bp-blue hover:bg-bp-blue hover:text-white transition-colors';
    buttons.appendChild(editBtn);
    buttons.appendChild(previewBtn);
    wrapper.insertBefore(buttons, area);

    const preview = document.createElement('div');
    preview.className = 'bp-card p-3';
    preview.style.display = 'none';
    wrapper.appendChild(preview);
    
    // Ensure textarea is visible initially
    area.style.display = 'block';

    let previewMode = false;
    const toggle = (mode) => {
      previewMode = mode !== undefined ? mode : !previewMode;
      console.log('Toggle mode:', previewMode ? 'preview' : 'edit');
      
      if (previewMode) {
        try {
          const html = DOMPurify.sanitize(marked.parse(area.value));
          preview.innerHTML = html;
          area.style.display = 'none';
          preview.style.display = 'block';
          // Update button styles
          editBtn.className = 'px-4 py-1 text-sm font-medium rounded border-2 border-bp-blue text-bp-blue hover:bg-bp-blue hover:text-white transition-colors';
          previewBtn.className = 'px-4 py-1 text-sm font-medium rounded bg-bp-blue text-white hover:bg-bp-blue-light transition-colors';
        } catch (error) {
          console.error('Error parsing markdown:', error);
          preview.innerHTML = '<p class="text-red-500">Error parsing markdown</p>';
        }
      } else {
        area.style.display = 'block';
        preview.style.display = 'none';
        // Update button styles
        editBtn.className = 'px-4 py-1 text-sm font-medium rounded bg-bp-blue text-white hover:bg-bp-blue-light transition-colors';
        previewBtn.className = 'px-4 py-1 text-sm font-medium rounded border-2 border-bp-blue text-bp-blue hover:bg-bp-blue hover:text-white transition-colors';
      }
    };

    editBtn.addEventListener('click', () => {
      console.log('Edit button clicked');
      toggle(false);
    });
    
    previewBtn.addEventListener('click', () => {
      console.log('Preview button clicked');
      toggle(true);
    });
  });
});

