// Modern Navigation JavaScript
function initNavigation() {
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

    // Meeting Action Dropdown Functionality
    function toggleDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        if (!dropdown) return;
        
        const isHidden = dropdown.classList.contains('hidden');
        
        // Close all other dropdowns first
        document.querySelectorAll('.dropdown-menu').forEach(menu => {
            if (menu.id !== dropdownId) {
                menu.classList.add('hidden');
                menu.setAttribute('aria-hidden', 'true');
            }
        });
        
        // Toggle current dropdown
        if (isHidden) {
            dropdown.classList.remove('hidden');
            dropdown.setAttribute('aria-hidden', 'false');
            
            // Position dropdown to stay within viewport
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
            
            // Focus first menu item for accessibility
            const firstMenuItem = dropdown.querySelector('[role="menuitem"]');
            if (firstMenuItem) {
                firstMenuItem.focus();
            }
        } else {
            dropdown.classList.add('hidden');
            dropdown.setAttribute('aria-hidden', 'true');
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
        else if (!e.target.closest('.relative')) {
            document.querySelectorAll('.dropdown-menu').forEach(menu => {
                menu.classList.add('hidden');
                menu.setAttribute('aria-hidden', 'true');
            });
        }
    });

    // Close dropdowns on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.dropdown-menu').forEach(menu => {
                menu.classList.add('hidden');
                menu.setAttribute('aria-hidden', 'true');
            });
        }
    });

    // Keyboard navigation for dropdowns
    document.addEventListener('keydown', function(e) {
        const activeDropdown = document.querySelector('.dropdown-menu:not(.hidden)');
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

document.addEventListener('DOMContentLoaded', initNavigation);
document.addEventListener('htmx:load', initNavigation);
