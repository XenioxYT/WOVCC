/**
 * Page Transitions & SPA Navigation
 * Handles smooth page transitions and prevents navbar/footer jumping
 * Includes proper cleanup to prevent memory leaks
 */

class PageTransitions {
    constructor() {
        this.isTransitioning = false;
        this.currentPage = window.location.pathname;
        this.cache = new Map();

        // Store bound handlers for cleanup
        this._clickHandler = this._handleClick.bind(this);
        this._popstateHandler = this._handlePopstate.bind(this);

        this.init();
    }

    init() {
        if ('scrollRestoration' in history) {
            history.scrollRestoration = 'manual';
        }

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

    /**
     * Cleanup method to remove event listeners and clear resources
     * Call this before creating a new instance to prevent memory leaks
     */
    destroy() {
        // Remove event listeners
        document.removeEventListener('click', this._clickHandler);
        window.removeEventListener('popstate', this._popstateHandler);

        // Clear page cache
        this.cache.clear();

        // Remove injected styles
        const style = document.getElementById('page-transition-styles');
        if (style) {
            style.remove();
        }

        // Reset state
        this.isTransitioning = false;
        this.currentPage = null;
    }

    injectStyles() {
        // Check if styles already exist to prevent duplicates
        if (document.getElementById('page-transition-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'page-transition-styles';
        style.textContent = `
            /* Page transition wrapper */
            #page-transition-wrapper {
                width: 100%;
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
                min-height: 60vh;
                transition: opacity 0.3s ease-in-out, transform 0.3s ease-in-out;
                width: 100%;
            }

            /* Footer stays at bottom */
            .footer {
                width: 100%;
            }

            /* Newsletter section stays at bottom */
            .newsletter-section {
                width: 100%;
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

            /* Ensure navbar stays sticky during transitions */
            /* Navbar must be a direct child of body for sticky to work properly */
            body > .navbar {
                position: -webkit-sticky;
                position: sticky;
                top: 0;
                z-index: 1000;
                will-change: transform; /* Hint to browser for better sticky performance */
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
        // Check if content is already wrapped
        if (document.querySelector('#page-transition-wrapper')) {
            return; // Already wrapped, don't wrap again
        }

        // Find the main content block (everything except navbar)
        const navbar = document.querySelector('.navbar');
        const newsletter = document.querySelector('.newsletter-section');
        const footer = document.querySelector('.footer');

        // Get all content between navbar and newsletter
        const contentElements = [];
        let currentElement = navbar ? navbar.nextElementSibling : document.body.firstElementChild;

        while (currentElement && currentElement !== newsletter) {
            if (currentElement.tagName !== 'SCRIPT' && currentElement !== navbar) {
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

        // Insert wrapper AFTER navbar (keeping navbar as direct child of body)
        if (navbar) {
            navbar.parentNode.insertBefore(wrapper, navbar.nextSibling);
        } else {
            document.body.appendChild(wrapper);
        }
    }

    /**
     * Internal click handler - extracted for cleanup
     */
    _handleClick(e) {
        const link = e.target.closest('a');

        if (!link) return;

        const href = link.getAttribute('href');
        console.log('[PageTransitions] Link clicked:', href);

        // Skip if:
        // - External link
        // - Hash link
        // - Special link (logout, etc)
        // - Download link
        // - Has target attribute
        // - URL has query parameters (like success=true from Stripe or token= for activation)
        if (!href ||
            href.startsWith('http') ||
            href.startsWith('#') ||
            href.startsWith('mailto:') ||
            href.startsWith('tel:') ||
            href.includes('?') || // Skip ALL URLs with query parameters to preserve them
            link.hasAttribute('target') ||
            link.hasAttribute('download') ||
            link.id === 'logout-btn') {
            console.log('[PageTransitions] Skipping navigation (external/special):', href);
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
            console.log('[PageTransitions] Intercepting navigation to:', href);
            e.preventDefault();
            this.navigateToPage(href);
        } else {
            console.log('[PageTransitions] Not intercepting (not nav/event link):', href);
        }
    }

    setupNavigationInterceptors() {
        // Intercept all internal link clicks using bound handler for cleanup
        document.addEventListener('click', this._clickHandler);
    }

    /**
     * Internal popstate handler - extracted for cleanup
     */
    _handlePopstate(e) {
        console.log('[PageTransitions] Popstate event:', e.state);
        if (e.state && e.state.path) {
            this.navigateToPage(e.state.path, false);
        }
    }

    setupHistoryNavigation() {
        // Use bound handler for cleanup
        window.addEventListener('popstate', this._popstateHandler);

        // Store initial state (preserve query parameters!)
        const fullPath = window.location.pathname + window.location.search;
        history.replaceState({ path: fullPath }, '', fullPath);
        console.log('[PageTransitions] Initial state stored with full path:', fullPath);
    }

    async navigateToPage(path, pushState = true) {
        console.log('[PageTransitions] navigateToPage called with path:', path, 'pushState:', pushState);

        if (this.isTransitioning || path === this.currentPage) {
            console.log('[PageTransitions] Skipping navigation (already transitioning or same page)');
            return;
        }

        console.log('[PageTransitions] Starting navigation transition to:', path);
        this.isTransitioning = true;
        // Set global flag so other scripts know SPA navigation is in progress
        window._spaNavigating = true;

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

            // --- REMOVED SCROLL FROM HERE ---

            // Update content
            this.updateContent(html, path);

            // --- MOVED SCROLL TO HERE ---
            // Scroll to top *after* new content is in the DOM.
            // We set all three possible scroll targets to be 100% certain.
            document.documentElement.scrollTop = 0; // The <html> element
            document.body.scrollTop = 0; // For Safari/older browsers
            window.scrollTo(0, 0); // Fallback

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
            // Reset global flag
            window._spaNavigating = false;

            // Force a final reflow to ensure navbar sticky positioning is correct
            // This fixes issues where navbar gets "stuck" mid-scroll
            const navbar = document.querySelector('.navbar');
            if (navbar) {
                void navbar.offsetHeight;
            }
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

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
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

            // Force reflow to ensure sticky navbar positioning is recalculated
            // This prevents the navbar from getting "stuck" during dynamic content updates
            void currentContent.offsetHeight;

            // Load external scripts first (in order)
            this.loadScriptsSequentially(scriptsToLoad).then(() => {
                // Wait a moment for external scripts to initialize
                setTimeout(() => {
                    // Skip inline scripts due to CSP - all scripts should be external files
                    if (inlineScripts.length > 0) {
                        console.warn('[PageTransitions] Inline scripts detected but skipped due to CSP policy');
                    }
                    // Legacy code below kept for reference but will not execute
                    /*
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
                    */

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

// Singleton pattern: destroy existing instance before creating new one
function initPageTransitions() {
    // Destroy existing instance if present to prevent memory leaks
    if (window.pageTransitions && typeof window.pageTransitions.destroy === 'function') {
        window.pageTransitions.destroy();
    }
    window.pageTransitions = new PageTransitions();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPageTransitions);
} else {
    initPageTransitions();
}
