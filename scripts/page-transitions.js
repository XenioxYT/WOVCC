/**
 * Page Transitions & SPA Navigation
 * Handles smooth page transitions and prevents navbar/footer jumping
 */

class PageTransitions {
    constructor() {
        this.isTransitioning = false;
        this.currentPage = window.location.pathname;
        this.cache = new Map();
        this.init();
    }

    init() {
        // Add page transition CSS
        this.injectStyles();
        
        // Add transition wrapper to content
        this.wrapContent();
        
        // Setup navigation interceptors
        this.setupNavigationInterceptors();
        
        // Handle browser back/forward
        this.setupHistoryNavigation();
        
        // Mark initial page as loaded
        document.body.classList.add('page-loaded');
    }

    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Page transition wrapper */
            #page-transition-wrapper {
                position: relative;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }

            /* Prevent layout shift during load */
            body:not(.page-loaded) #page-transition-wrapper {
                opacity: 0;
            }

            body.page-loaded #page-transition-wrapper {
                opacity: 1;
                transition: opacity 0.3s ease-in-out;
            }

            /* Content wrapper to prevent footer jumping */
            .page-content-wrapper {
                flex: 1 0 auto;
                min-height: 60vh;
                transition: opacity 0.3s ease-in-out, transform 0.3s ease-in-out;
            }

            /* Footer stays at bottom */
            .footer {
                flex-shrink: 0;
            }

            /* Newsletter section stays at bottom */
            .newsletter-section {
                flex-shrink: 0;
            }

            /* Transition states */
            body.page-transitioning .page-content-wrapper {
                opacity: 0;
                transform: translateY(20px);
            }

            /* Skeleton loaders maintain height */
            .skeleton-height-maintainer {
                min-height: 400px;
            }

            /* Smooth height transitions for dynamic content */
            #live-match-section,
            #no-match-section {
                transition: opacity 0.3s ease-in-out;
            }

            /* Prevent content jumping during async loads */
            .content-loading {
                min-height: 300px;
                position: relative;
            }

            .content-loading::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(
                    90deg,
                    rgba(233, 236, 239, 0) 0%,
                    rgba(233, 236, 239, 0.3) 50%,
                    rgba(233, 236, 239, 0) 100%
                );
                animation: shimmer 1.5s infinite;
            }

            @keyframes shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }

            /* Ensure navbar stays fixed during transitions */
            .navbar {
                position: sticky;
                top: 0;
                z-index: 1000;
                will-change: transform;
            }

            /* Prevent flash of login screen on auth pages during page load/transitions */
            /* These sections will be shown by JavaScript after auth check completes */
            body:not(.auth-checked) #login-section,
            body:not(.auth-checked) #members-content,
            body:not(.auth-checked) #access-denied-section,
            body:not(.auth-checked) #admin-content {
                visibility: hidden !important;
            }

            /* After auth is checked, make them visible again (JS will handle display) */
            body.auth-checked #login-section,
            body.auth-checked #members-content,
            body.auth-checked #access-denied-section,
            body.auth-checked #admin-content {
                visibility: visible !important;
            }
        `;
        document.head.appendChild(style);
    }

    wrapContent() {
        // Find the main content block (everything except navbar)
        const navbar = document.querySelector('.navbar');
        const newsletter = document.querySelector('.newsletter-section');
        const footer = document.querySelector('.footer');
        
        // Get all content between navbar and newsletter
        const contentElements = [];
        let currentElement = navbar ? navbar.nextElementSibling : document.body.firstElementChild;
        
        while (currentElement && currentElement !== newsletter) {
            if (currentElement.tagName !== 'SCRIPT') {
                contentElements.push(currentElement);
            }
            currentElement = currentElement.nextElementSibling;
        }

        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.id = 'page-transition-wrapper';
        
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'page-content-wrapper';
        contentWrapper.id = 'page-content-wrapper';
        
        // Move content into wrapper
        contentElements.forEach(el => {
            contentWrapper.appendChild(el);
        });
        
        wrapper.appendChild(contentWrapper);
        
        // Add newsletter and footer to wrapper
        if (newsletter) {
            wrapper.appendChild(newsletter);
        }
        if (footer) {
            wrapper.appendChild(footer);
        }
        
        // Insert wrapper
        if (navbar) {
            navbar.parentNode.insertBefore(wrapper, navbar.nextSibling);
        } else {
            document.body.appendChild(wrapper);
        }
    }

    setupNavigationInterceptors() {
        // Intercept all internal link clicks
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            
            if (!link) return;
            
            const href = link.getAttribute('href');
            
            // Skip if:
            // - External link
            // - Hash link
            // - Special link (logout, etc)
            // - Download link
            // - Has target attribute
            // - URL has query parameters (like success=true from Stripe)
            if (!href || 
                href.startsWith('http') || 
                href.startsWith('#') || 
                href.startsWith('mailto:') ||
                href.startsWith('tel:') ||
                (href.includes('?success=true') || href.includes('?canceled=true')) || // Skip for Stripe redirect URLs
                link.hasAttribute('target') ||
                link.hasAttribute('download') ||
                link.id === 'logout-btn') {
                return;
            }
            
            // Check if it's a navigation link in the navbar
            const isNavLink = link.classList.contains('nav-link') || 
                            link.closest('.navbar') ||
                            link.closest('.btn');
            
            // Check if it's an event card or other internal navigation
            const isEventCard = link.closest('.event-card') || 
                              href.startsWith('/events/') ||
                              href.startsWith('/matches') ||
                              href.startsWith('/members') ||
                              href.startsWith('/join') ||
                              href.startsWith('/admin') ||
                              href === '/';
            
            if (isNavLink || isEventCard) {
                e.preventDefault();
                this.navigateToPage(href);
            }
        });
    }

    setupHistoryNavigation() {
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.path) {
                this.navigateToPage(e.state.path, false);
            }
        });
        
        // Store initial state
        history.replaceState({ path: window.location.pathname }, '', window.location.pathname);
    }

    async navigateToPage(path, pushState = true) {
        if (this.isTransitioning || path === this.currentPage) {
            return;
        }

        this.isTransitioning = true;
        document.body.classList.add('page-transitioning');
        // Remove auth-checked class so new page can re-check auth without flash
        document.body.classList.remove('auth-checked');

        // Dispatch event to notify other components that transition is starting
        const startEvent = new CustomEvent('pageTransitionStart', {
            detail: { path }
        });
        document.dispatchEvent(startEvent);

        try {
            // Fetch new page content
            const html = await this.fetchPage(path);
            
            // Wait for fade-out transition to complete
            await this.sleep(300);
            
            // Scroll to top immediately after fade-out, before new content loads
            window.scrollTo({ top: 0, behavior: 'instant' });
            
            // Update content
            this.updateContent(html, path);
            
            // Update browser history
            if (pushState) {
                history.pushState({ path }, '', path);
            }
            
            // Update current page
            this.currentPage = path;
            
            // Update active nav link
            this.updateActiveNavLink(path);
            
        } catch (error) {
            console.error('Navigation error:', error);
            // Fallback to traditional navigation
            window.location.href = path;
        } finally {
            // Remove transitioning state after a brief delay to allow new page animations
            await this.sleep(100);
            document.body.classList.remove('page-transitioning');
            this.isTransitioning = false;
        }
    }

    async fetchPage(path) {
        const noCachePaths = ['/events', '/admin'];
        const isUncacheable = noCachePaths.some(p => path.startsWith(p));

        // Use cache only for cacheable paths
        if (!isUncacheable && this.cache.has(path)) {
            return this.cache.get(path);
        }

        const fetchOptions = {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        // For uncacheable paths, bypass browser cache
        if (isUncacheable) {
            fetchOptions.headers['Cache-Control'] = 'no-cache';
        }

        const response = await fetch(path, fetchOptions);

        if (!response.ok) {            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const html = await response.text();
        
        // Cache the response only for cacheable paths
        if (!isUncacheable) {
            if (this.cache.size > 10) {
                const firstKey = this.cache.keys().next().value;
                this.cache.delete(firstKey);
            }
            this.cache.set(path, html);
        }

        return html;
    }

    updateContent(html, path) {
        // Parse the HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract the content from body (everything between navbar and newsletter/footer)
        const newBodyContent = doc.body;
        
        // Get current content wrapper
        const currentContent = document.querySelector('#page-content-wrapper');
        
        if (newBodyContent && currentContent) {
            // Find all content sections (everything except navbar, scripts, newsletter, footer)
            const contentSections = [];
            const scriptsToLoad = [];
            const inlineScripts = [];
            
            Array.from(newBodyContent.children).forEach(child => {
                const tagName = child.tagName.toLowerCase();
                const className = child.className || '';
                
                // Skip navbar, newsletter, footer, and initial scripts
                if (tagName === 'nav' || 
                    className.includes('navbar') ||
                    className.includes('newsletter-section') ||
                    className.includes('footer') ||
                    child.id === 'page-transition-wrapper') {
                    return;
                }
                
                // Collect scripts to execute later
                if (tagName === 'script') {
                    if (child.src) {
                        // External script
                        const src = child.src;
                        // Skip if it's a common script already loaded (auth, main, api-client, etc)
                        if (!this.isScriptAlreadyLoaded(src)) {
                            scriptsToLoad.push(child);
                        }
                    } else {
                        // Inline script
                        inlineScripts.push(child);
                    }
                } else {
                    // This is actual content
                    contentSections.push(child);
                }
            });
            
            // Clear current content
            currentContent.innerHTML = '';
            
            // Add new content sections
            contentSections.forEach(section => {
                currentContent.appendChild(section.cloneNode(true));
            });
            
            // Load external scripts first (in order)
            this.loadScriptsSequentially(scriptsToLoad).then(() => {
                // Wait a moment for external scripts to initialize
                setTimeout(() => {
                    // Then execute inline scripts
                    inlineScripts.forEach((oldScript, index) => {
                        try {
                            const newScript = document.createElement('script');
                            newScript.textContent = oldScript.textContent;
                            
                            // Copy any attributes
                            Array.from(oldScript.attributes).forEach(attr => {
                                newScript.setAttribute(attr.name, attr.value);
                            });
                            
                            // Add to page and it will execute
                            document.body.appendChild(newScript);
                            
                            // Clean up after execution
                            setTimeout(() => {
                                if (newScript.parentNode) {
                                    newScript.remove();
                                }
                            }, 500);
                        } catch (error) {
                            console.error('Error executing inline script:', error);
                        }
                    });
                    
                    // After all scripts are loaded and executed, dispatch the event
                    setTimeout(() => {
                        this.initializePageScripts(path);
                    }, 200);
                }, 100);
            }).catch(error => {
                console.error('Error loading external scripts:', error);
            });
            
            // Update title
            const newTitle = doc.querySelector('title');
            if (newTitle) {
                document.title = newTitle.textContent;
            }
            
            // Update meta description
            const newDescription = doc.querySelector('meta[name="description"]');
            const currentDescription = document.querySelector('meta[name="description"]');
            if (newDescription && currentDescription) {
                currentDescription.setAttribute('content', newDescription.getAttribute('content'));
            }
        }
    }

    isScriptAlreadyLoaded(src) {
        // Check if script with this src is already in the document
        const scripts = document.querySelectorAll('script[src]');
        for (let script of scripts) {
            if (script.src === src || script.getAttribute('src') === src) {
                return true;
            }
        }
        return false;
    }

    async loadScriptsSequentially(scriptElements) {
        // Load scripts one by one to maintain order
        for (let oldScript of scriptElements) {
            await this.loadScript(oldScript);
        }
    }

    loadScript(oldScript) {
        return new Promise((resolve, reject) => {
            const newScript = document.createElement('script');
            
            // Copy attributes
            Array.from(oldScript.attributes).forEach(attr => {
                newScript.setAttribute(attr.name, attr.value);
            });
            
            newScript.onload = () => resolve();
            newScript.onerror = () => {
                console.error('Failed to load script:', oldScript.src);
                resolve(); // Continue even if script fails
            };
            
            // Add to page
            document.body.appendChild(newScript);
        });
    }

    updateActiveNavLink(path) {
        // Remove all active classes
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Add active class to current page
        document.querySelectorAll('.nav-link').forEach(link => {
            const href = link.getAttribute('href');
            if (href === path || (path === '/' && href === '/')) {
                link.classList.add('active');
            }
        });
    }

    initializePageScripts(path) {
        // Dispatch custom event for page load
        const event = new CustomEvent('pageTransitionComplete', {
            detail: { path }
        });
        document.dispatchEvent(event);
        
        // Re-initialize common scripts
        if (typeof highlightActivePage === 'function') {
            highlightActivePage();
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pageTransitions = new PageTransitions();
    });
} else {
    window.pageTransitions = new PageTransitions();
}
