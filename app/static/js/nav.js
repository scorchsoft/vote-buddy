// Modern Navigation JavaScript
function initNav() {
    // Mobile Navigation Toggle
    const navToggle = document.getElementById('nav-toggle');
    const navDrawerMobile = document.getElementById('nav-drawer-mobile');
    const body = document.body;
    
    if (navToggle && navDrawerMobile) {
        // Remove any existing click listeners to prevent duplicates
        const newNavToggle = navToggle.cloneNode(true);
        navToggle.parentNode.replaceChild(newNavToggle, navToggle);
        
        // Toggle mobile menu
        newNavToggle.addEventListener('click', function() {
            const isOpen = newNavToggle.getAttribute('aria-expanded') === 'true';
            
            newNavToggle.setAttribute('aria-expanded', !isOpen);
            navDrawerMobile.hidden = isOpen;
            
            if (!isOpen) {
                navDrawerMobile.classList.add('open');
                // Create overlay
                const overlay = document.createElement('div');
                overlay.className = 'nav-overlay';
                overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 30; transition: opacity 0.3s;';
                overlay.style.opacity = '0';
                overlay.onclick = () => newNavToggle.click();
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
    }
    
    // Theme Toggle - Always restore theme state
    const html = document.documentElement;
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    // Always apply the theme state
    if (currentTheme === 'dark') {
        html.classList.add('dark');
        html.setAttribute('data-theme', 'dark');
    } else {
        html.classList.remove('dark');
        html.setAttribute('data-theme', 'light');
    }
    
    // Set up theme toggle button
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    
    if (themeToggle && themeIcon) {
        // Remove any existing click listeners to prevent duplicates
        const newThemeToggle = themeToggle.cloneNode(true);
        const newThemeIcon = newThemeToggle.querySelector('img');
        themeToggle.parentNode.replaceChild(newThemeToggle, themeToggle);
        
        // Update icon based on theme
        const updateThemeIcon = (isDark) => {
            newThemeIcon.src = isDark ? newThemeIcon.dataset.sun : newThemeIcon.dataset.moon;
            newThemeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            // Remove invert class when in dark mode since sun should be white
            if (isDark) {
                newThemeIcon.classList.remove('invert');
            } else {
                newThemeIcon.classList.add('invert');
            }
        };
        
        updateThemeIcon(currentTheme === 'dark');
        
        // Theme toggle click handler
        newThemeToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const isDark = !html.classList.contains('dark');
            
            if (isDark) {
                html.classList.add('dark');
                html.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                html.classList.remove('dark');
                html.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
            
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

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initNav);

// Re-initialize after HTMX navigation
document.body.addEventListener('htmx:load', initNav);

// Preserve dark mode class on HTMX requests
document.body.addEventListener('htmx:beforeSwap', function(evt) {
    // Store current dark mode state
    const isDark = document.documentElement.classList.contains('dark');
    
    // After swap, restore dark mode state
    setTimeout(() => {
        if (isDark) {
            document.documentElement.classList.add('dark');
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.setAttribute('data-theme', 'light');
        }
    }, 0);
});

// Global escape key handler
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const navToggle = document.getElementById('nav-toggle');
        if (navToggle && navToggle.getAttribute('aria-expanded') === 'true') {
            navToggle.click();
        }
    }
});
