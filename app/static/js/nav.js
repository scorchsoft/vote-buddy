// Modern Navigation JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Mobile Navigation Toggle
    const navToggle = document.getElementById('nav-toggle');
    const navDrawer = document.getElementById('nav-drawer');
    const body = document.body;
    
    if (navToggle && navDrawer) {
        // Toggle mobile menu
        navToggle.addEventListener('click', function() {
            const isOpen = navToggle.getAttribute('aria-expanded') === 'true';
            
            navToggle.setAttribute('aria-expanded', !isOpen);
            navDrawer.hidden = isOpen;
            
            if (!isOpen) {
                navDrawer.classList.add('open');
                // Create overlay
                const overlay = document.createElement('div');
                overlay.className = 'nav-overlay';
                overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 30; transition: opacity 0.3s;';
                overlay.onclick = () => navToggle.click();
                body.appendChild(overlay);
                
                // Animate overlay
                requestAnimationFrame(() => overlay.style.opacity = '1');
                
                // Trap focus
                navDrawer.focus();
            } else {
                navDrawer.classList.remove('open');
                // Remove overlay
                const overlay = document.querySelector('.nav-overlay');
                if (overlay) {
                    overlay.style.opacity = '0';
                    setTimeout(() => overlay.remove(), 300);
                }
            }
        });
        
        // Close on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && navToggle.getAttribute('aria-expanded') === 'true') {
                navToggle.click();
            }
        });
    }
    
    // Theme Toggle
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const html = document.documentElement;
    
    // Check for saved theme preference
    const currentTheme = localStorage.getItem('theme') || 'light';
    html.classList.toggle('dark', currentTheme === 'dark');
    
    if (themeToggle && themeIcon) {
        // Update icon based on theme
        const updateThemeIcon = (isDark) => {
            themeIcon.src = isDark ? themeIcon.dataset.sun : themeIcon.dataset.moon;
            themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        };
        
        updateThemeIcon(currentTheme === 'dark');
        
        // Theme toggle click handler
        themeToggle.addEventListener('click', function() {
            const isDark = html.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            updateThemeIcon(isDark);
            
            // Add transition effect
            html.style.transition = 'background-color 0.3s, color 0.3s';
            setTimeout(() => html.style.transition = '', 300);
        });
    }
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update URL without jumping
                history.pushState(null, null, targetId);
            }
        });
    });
    
    // Highlight current section on scroll
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('a[href^="#"]');
    
    if (sections.length > 0) {
        const highlightSection = () => {
            const scrollY = window.pageYOffset;
            
            sections.forEach(section => {
                const sectionHeight = section.offsetHeight;
                const sectionTop = section.offsetTop - 100;
                const sectionId = section.getAttribute('id');
                
                if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                    navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === `#${sectionId}`) {
                            link.classList.add('active');
                        }
                    });
                }
            });
        };
        
        window.addEventListener('scroll', highlightSection);
        highlightSection();
    }
    
    // Add loading states to forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!this.hasAttribute('hx-post') && !this.hasAttribute('hx-get')) {
                const submitBtn = this.querySelector('[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="bp-spinner inline-block w-4 h-4 mr-2"></span>Loading...';
                }
            }
        });
    });
    
    // Enhanced tooltips
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        let tooltipTimeout;
        
        el.addEventListener('mouseenter', function() {
            tooltipTimeout = setTimeout(() => {
                this.classList.add('tooltip-visible');
            }, 500);
        });
        
        el.addEventListener('mouseleave', function() {
            clearTimeout(tooltipTimeout);
            this.classList.remove('tooltip-visible');
        });
    });
});
