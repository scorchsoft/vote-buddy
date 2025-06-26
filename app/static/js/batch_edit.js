function toggleSection(sectionId) {
  const section = document.getElementById(sectionId);
  const icon = document.getElementById(sectionId + '-icon');
  
  if (section.style.display === 'none') {
    section.style.display = 'block';
    icon.style.transform = 'rotate(0deg)';
  } else {
    section.style.display = 'none';
    icon.style.transform = 'rotate(-90deg)';
  }
}

// Initialize all sections as expanded
function initBatchEdit() {
  // Get all motion sections and expand them
  const motionSections = document.querySelectorAll('[id^="motion-"]');
  motionSections.forEach(function(section) {
    if (section.id.match(/^motion-\d+$/)) {
      section.style.display = 'block';
    }
  });
}

// Initialize when DOM is ready
if (document.readyState !== 'loading') {
  initBatchEdit();
} else {
  document.addEventListener('DOMContentLoaded', initBatchEdit);
} 