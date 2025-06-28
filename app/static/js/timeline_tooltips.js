document.addEventListener('DOMContentLoaded', function() {
  // Wait a bit for DOM to be fully ready
  setTimeout(function() {
    const tooltip = document.getElementById('timeline-tooltip');
    const clickableElements = document.querySelectorAll('.timeline-clickable');
    
    console.log('Timeline tooltip setup:', {
      tooltip: !!tooltip,
      clickableCount: clickableElements.length
    });
    
    if (!tooltip) {
      console.error('Timeline tooltip element not found');
      return;
    }
    
    clickableElements.forEach(element => {
      element.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Timeline label clicked:', this.getAttribute('data-timeline-title'));
        showTooltip(this, e);
      });
      
      element.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          showTooltip(this, e);
        }
      });
    });
    
    function showTooltip(element, event) {
      const title = element.getAttribute('data-timeline-title');
      const content = element.getAttribute('data-timeline-explanation');
      
      console.log('Showing tooltip:', { title, content });
      
      // Hide any existing tooltip first
      tooltip.classList.remove('show');
      
      // Set content
      tooltip.querySelector('.timeline-tooltip-title').textContent = title;
      tooltip.querySelector('.timeline-tooltip-content').textContent = content;
      
      // Show tooltip first to get dimensions
      tooltip.style.visibility = 'hidden';
      tooltip.style.opacity = '1';
      tooltip.classList.add('show');
      
      // Position tooltip
      const rect = element.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
      
      // Position above the element
      let left = rect.left + scrollLeft + (rect.width / 2) - (tooltipRect.width / 2);
      let top = rect.top + scrollTop - tooltipRect.height - 15;
      
      // Keep tooltip within viewport
      left = Math.max(10, Math.min(left, window.innerWidth - tooltipRect.width - 10));
      top = Math.max(10, top);
      
      // If tooltip would be above viewport, position below element instead
      if (top < scrollTop + 10) {
        top = rect.bottom + scrollTop + 15;
        // Move arrow to top
        tooltip.querySelector('.timeline-tooltip-arrow').style.top = '-5px';
        tooltip.querySelector('.timeline-tooltip-arrow').style.bottom = 'auto';
      } else {
        // Arrow at bottom (default)
        tooltip.querySelector('.timeline-tooltip-arrow').style.top = 'auto';
        tooltip.querySelector('.timeline-tooltip-arrow').style.bottom = '-5px';
      }
      
      tooltip.style.left = left + 'px';
      tooltip.style.top = top + 'px';
      tooltip.style.visibility = 'visible';
      
      console.log('Tooltip positioned at:', { left, top });
      
      // Hide tooltip after 8 seconds
      setTimeout(() => {
        tooltip.classList.remove('show');
      }, 8000);
    }
    
    // Hide tooltip when clicking outside
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.timeline-clickable') && !e.target.closest('.timeline-tooltip')) {
        tooltip.classList.remove('show');
      }
    });
    
    // Hide tooltip on escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        tooltip.classList.remove('show');
      }
    });
  }, 100);
}); 