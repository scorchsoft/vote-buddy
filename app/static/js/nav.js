// Modern Navigation JavaScript
function initNav() {
    // Mobile Navigation Toggle
    const navToggle = document.getElementById('nav-toggle');
    const navDrawerMobile = document.getElementById('nav-drawer-mobile');
    const body = document.body;
    
    if (navToggle && navDrawerMobile) {
        // Toggle mobile menu
        navToggle.addEventListener('click', function() {
            const isOpen = navToggle.getAttribute('aria-expanded') === 'true';
            
            navToggle.setAttribute('aria-expanded', !isOpen);
            navDrawerMobile.hidden = isOpen;
            
            if (!isOpen) {
                navDrawerMobile.classList.add('open');
                // Create overlay
                const overlay = document.createElement('div');
                overlay.className = 'nav-overlay';
                overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 30; transition: opacity 0.3s;';
                overlay.style.opacity = '0';
                overlay.onclick = () => navToggle.click();
                body.appendChild(overlay);
                
                // Animate overlay
                requestAnimationFrame(() => {
                    overlay.style.opacity = '1';
                });
                
                // Prevent body scroll
                body.style.overflow = 'hidden';
            } else {
                navDrawerMobile.classList.remove('open');
                // Remove overlay
                const overlay = document.querySelector('.nav-overlay');
                if (overlay) {
                    overlay.style.opacity = '0';
                    setTimeout(() => overlay.remove(), 300);
                }
                // Restore body scroll
                body.style.overflow = '';
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
    // Also set data attribute for broader CSS support
    html.setAttribute('data-theme', currentTheme);
    
    if (themeToggle && themeIcon) {
        // Update icon based on theme
        const updateThemeIcon = (isDark) => {
            themeIcon.src = isDark ? themeIcon.dataset.sun : themeIcon.dataset.moon;
            themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            // Remove invert class when in dark mode since sun should be white
            if (isDark) {
                themeIcon.classList.remove('invert');
            } else {
                themeIcon.classList.add('invert');
            }
        };
        
        updateThemeIcon(currentTheme === 'dark');
        
        // Theme toggle click handler
        themeToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const isDark = html.classList.toggle('dark');
            const newTheme = isDark ? 'dark' : 'light';
            localStorage.setItem('theme', newTheme);
            html.setAttribute('data-theme', newTheme);
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

    // Meeting Action Dropdown Functionality
    function toggleDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        if (!dropdown) return;
        
        const dropdownContainer = dropdown.closest('.bp-dropdown');
        if (!dropdownContainer) return;
        
        const isActive = dropdownContainer.classList.contains('dropdown-active');
        
        // Close all other dropdowns first
        document.querySelectorAll('.bp-dropdown.dropdown-active').forEach(container => {
            if (container !== dropdownContainer) {
                container.classList.remove('dropdown-active');
                const menu = container.querySelector('.bp-dropdown-menu');
                if (menu) {
                    menu.setAttribute('aria-hidden', 'true');
                }
                // Update trigger button state
                const trigger = container.querySelector('.dropdown-trigger');
                if (trigger) {
                    trigger.setAttribute('aria-expanded', 'false');
                }
            }
        });
        
        // Toggle current dropdown
        const trigger = dropdownContainer.querySelector('.dropdown-trigger');
        if (!isActive) {
            dropdownContainer.classList.add('dropdown-active');
            dropdown.removeAttribute('aria-hidden');
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'true');
            }
            
            // Position dropdown to stay within viewport
            setTimeout(() => {
                const rect = dropdown.getBoundingClientRect();
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                
                // Adjust horizontal position if dropdown would go off-screen
                if (rect.right > viewportWidth) {
                    dropdown.style.left = 'auto';
                    dropdown.style.right = '0';
                }
                
                // Adjust vertical position if dropdown would go off-screen
                if (rect.bottom > viewportHeight) {
                    dropdown.style.top = 'auto';
                    dropdown.style.bottom = '100%';
                    dropdown.style.marginBottom = '0.5rem';
                }
            }, 0);
        } else {
            dropdownContainer.classList.remove('dropdown-active');
            dropdown.setAttribute('aria-hidden', 'true');
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'false');
                trigger.focus(); // Return focus to trigger
            }
        }
    }

    // Event delegation for dropdown triggers
    document.addEventListener('click', function(e) {
        const trigger = e.target.closest('.dropdown-trigger');
        if (trigger) {
            e.preventDefault();
            e.stopPropagation();
            const targetId = trigger.getAttribute('data-dropdown-target');
            if (targetId) {
                toggleDropdown(targetId);
            }
        }
        // Close dropdowns when clicking outside
        else if (!e.target.closest('.bp-dropdown')) {
            document.querySelectorAll('.bp-dropdown.dropdown-active').forEach(container => {
                container.classList.remove('dropdown-active');
                const menu = container.querySelector('.bp-dropdown-menu');
                if (menu) {
                    menu.setAttribute('aria-hidden', 'true');
                }
                // Update trigger button state
                const trigger = container.querySelector('.dropdown-trigger');
                if (trigger) {
                    trigger.setAttribute('aria-expanded', 'false');
                }
            });
        }
    });

    // Close dropdowns on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.bp-dropdown.dropdown-active').forEach(container => {
                container.classList.remove('dropdown-active');
                const menu = container.querySelector('.bp-dropdown-menu');
                if (menu) {
                    menu.setAttribute('aria-hidden', 'true');
                }
                // Update trigger button state and return focus
                const trigger = container.querySelector('.dropdown-trigger');
                if (trigger) {
                    trigger.setAttribute('aria-expanded', 'false');
                    trigger.focus();
                }
            });
        }
    });

    // Keyboard navigation for dropdowns
    document.addEventListener('keydown', function(e) {
        const activeContainer = document.querySelector('.bp-dropdown.dropdown-active');
        if (!activeContainer) return;
        const activeDropdown = activeContainer.querySelector('.bp-dropdown-menu');
        if (!activeDropdown) return;
        
        const menuItems = activeDropdown.querySelectorAll('[role="menuitem"]');
        const currentIndex = Array.from(menuItems).findIndex(item => item === document.activeElement);
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = currentIndex < menuItems.length - 1 ? currentIndex + 1 : 0;
                menuItems[nextIndex].focus();
                break;
            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = currentIndex > 0 ? currentIndex - 1 : menuItems.length - 1;
                menuItems[prevIndex].focus();
                break;
            case 'Home':
                e.preventDefault();
                menuItems[0].focus();
                break;
            case 'End':
                e.preventDefault();
                menuItems[menuItems.length - 1].focus();
                break;
        }
    });
}

document.addEventListener('DOMContentLoaded', initNav);
document.body.addEventListener('htmx:load', initNav);
