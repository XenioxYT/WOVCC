/**
 * Footer Animations
 * Animates newsletter and footer sections on page load
 * Works with dynamic page loading via page-transitions.js
 */

class FooterAnimations {
  constructor() {
    this.newsletterSection = null;
    this.footerSection = null;
    this.animated = false;
    this.observer = null;
    this.init();
  }

  init() {
    // Add animation styles
    this.injectStyles();
    
    // Initial page load
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.setupFooterElements();
        this.observePageLoad();
      });
    } else {
      this.setupFooterElements();
      this.observePageLoad();
    }

    // Listen for page transition start to fade out footers
    document.addEventListener('pageTransitionStart', () => {
      this.fadeOutFooters();
    });

    // Handle page transition complete to animate in footers
    document.addEventListener('pageTransitionComplete', () => {
      this.resetAnimations();
      this.setupFooterElements();
      this.observePageLoad();
    });
  }

  injectStyles() {
    const style = document.createElement('style');
    style.id = 'footer-animation-styles';
    style.textContent = `
      /* Footer animation initial state */
      .newsletter-section,
      .footer {
        opacity: 0;
        transform: translateY(30px);
        transition: opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1),
                    transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
      }

      /* Transitioning state - fade out quickly with page content */
      .newsletter-section.footer-transitioning,
      .footer.footer-transitioning {
        opacity: 0 !important;
        transform: translateY(0) !important;
        transition: opacity 0.3s ease-in-out !important;
      }

      /* Animated state */
      .newsletter-section.footer-animated,
      .footer.footer-animated {
        opacity: 1;
        transform: translateY(0);
      }

      /* Stagger the newsletter slightly before footer */
      .newsletter-section.footer-animated {
        transition-delay: 0.1s;
      }

      .footer.footer-animated {
        transition-delay: 0.2s;
      }

      /* Ensure footer content doesn't jump */
      .newsletter-section {
        will-change: opacity, transform;
      }

      .footer {
        will-change: opacity, transform;
      }

      /* Prevent flash of unstyled content */
      body:not(.page-loaded) .newsletter-section,
      body:not(.page-loaded) .footer {
        opacity: 0;
      }

      /* Animate footer content items */
      .footer-section {
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1) 0.3s,
                    transform 0.5s cubic-bezier(0.4, 0, 0.2, 1) 0.3s;
      }

      .footer.footer-animated .footer-section {
        opacity: 1;
        transform: translateY(0);
      }

      /* Reset footer sections during transition */
      .footer.footer-transitioning .footer-section {
        opacity: 0 !important;
        transform: translateY(0) !important;
        transition: opacity 0.3s ease-in-out !important;
      }

      /* Stagger footer sections */
      .footer.footer-animated .footer-section:nth-child(1) {
        transition-delay: 0.35s;
      }

      .footer.footer-animated .footer-section:nth-child(2) {
        transition-delay: 0.45s;
      }

      .footer.footer-animated .footer-section:nth-child(3) {
        transition-delay: 0.55s;
      }

      .footer.footer-animated .footer-section:nth-child(4) {
        transition-delay: 0.65s;
      }

      /* Newsletter content animation */
      .newsletter-content h2,
      .newsletter-content p,
      .newsletter-form-main {
        opacity: 0;
        transform: translateY(15px);
        transition: opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1),
                    transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
      }

      .newsletter-section.footer-animated .newsletter-content h2 {
        opacity: 1;
        transform: translateY(0);
        transition-delay: 0.25s;
      }

      .newsletter-section.footer-animated .newsletter-content p {
        opacity: 1;
        transform: translateY(0);
        transition-delay: 0.35s;
      }

      .newsletter-section.footer-animated .newsletter-form-main {
        opacity: 1;
        transform: translateY(0);
        transition-delay: 0.45s;
      }

      /* Reset newsletter content during transition */
      .newsletter-section.footer-transitioning .newsletter-content h2,
      .newsletter-section.footer-transitioning .newsletter-content p,
      .newsletter-section.footer-transitioning .newsletter-form-main {
        opacity: 0 !important;
        transform: translateY(0) !important;
        transition: opacity 0.3s ease-in-out !important;
      }

      /* Social links animation */
      .social-link {
        opacity: 0;
        transform: scale(0.8);
        transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                    transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      }

      .footer.footer-animated .social-link {
        opacity: 1;
        transform: scale(1);
      }

      /* Reset social links during transition */
      .footer.footer-transitioning .social-link {
        opacity: 0 !important;
        transform: scale(1) !important;
        transition: opacity 0.3s ease-in-out !important;
      }

      .footer.footer-animated .social-link:nth-child(1) {
        transition-delay: 0.7s;
      }

      .footer.footer-animated .social-link:nth-child(2) {
        transition-delay: 0.75s;
      }

      .footer.footer-animated .social-link:nth-child(3) {
        transition-delay: 0.8s;
      }

      .footer.footer-animated .social-link:nth-child(4) {
        transition-delay: 0.85s;
      }

      /* Footer bottom animation */
      .footer-bottom {
        opacity: 0;
        transform: translateY(10px);
        transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1) 0.75s,
                    transform 0.4s cubic-bezier(0.4, 0, 0.2, 1) 0.75s;
      }

      .footer.footer-animated .footer-bottom {
        opacity: 1;
        transform: translateY(0);
      }

      /* Reset footer bottom during transition */
      .footer.footer-transitioning .footer-bottom {
        opacity: 0 !important;
        transform: translateY(0) !important;
        transition: opacity 0.3s ease-in-out !important;
      }

      /* Reduce motion for accessibility */
      @media (prefers-reduced-motion: reduce) {
        .newsletter-section,
        .footer,
        .footer-section,
        .newsletter-content h2,
        .newsletter-content p,
        .newsletter-form-main,
        .social-link,
        .footer-bottom {
          transition-duration: 0.01ms !important;
          transition-delay: 0s !important;
          animation-duration: 0.01ms !important;
          animation-delay: 0s !important;
        }
      }
    `;
    
    // Remove existing style if present
    const existingStyle = document.getElementById('footer-animation-styles');
    if (existingStyle) {
      existingStyle.remove();
    }
    
    document.head.appendChild(style);
  }

  setupFooterElements() {
    this.newsletterSection = document.querySelector('.newsletter-section');
    this.footerSection = document.querySelector('.footer');
  }

  fadeOutFooters() {
    // Immediately fade out footers when page transition starts
    if (this.newsletterSection) {
      this.newsletterSection.classList.remove('footer-animated');
      this.newsletterSection.classList.add('footer-transitioning');
    }
    
    if (this.footerSection) {
      this.footerSection.classList.remove('footer-animated');
      this.footerSection.classList.add('footer-transitioning');
    }
  }

  resetAnimations() {
    this.animated = false;
    
    // Disconnect any existing observer
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    
    if (this.newsletterSection) {
      this.newsletterSection.classList.remove('footer-animated', 'footer-transitioning');
    }
    
    if (this.footerSection) {
      this.footerSection.classList.remove('footer-animated', 'footer-transitioning');
    }
  }

  observePageLoad() {
    // Wait for page content to load, then set up intersection observer
    this.waitForPageContent().then(() => {
      this.setupIntersectionObserver();
    });

    // Fallback - set up observer after maximum timeout
    setTimeout(() => {
      if (!this.animated) {
        this.setupIntersectionObserver();
      }
    }, 2000);
  }

  setupIntersectionObserver() {
    // Don't set up if already animated
    if (this.animated) return;

    // Disconnect any existing observer
    if (this.observer) {
      this.observer.disconnect();
    }

    // Ensure elements are set up
    if (!this.newsletterSection || !this.footerSection) {
      this.setupFooterElements();
    }

    // If elements still don't exist, bail out
    if (!this.newsletterSection && !this.footerSection) return;

    // Create intersection observer
    const options = {
      root: null, // viewport
      rootMargin: '0px 0px -100px 0px', // Trigger when element is 100px from bottom of viewport
      threshold: 0.15 // Trigger when 15% of element is visible
    };

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !this.animated) {
          this.animateFooters();
          // Disconnect observer after animation to prevent re-triggering
          if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
          }
        }
      });
    }, options);

    // Observe the newsletter section (which comes first)
    if (this.newsletterSection) {
      this.observer.observe(this.newsletterSection);
    } else if (this.footerSection) {
      // Fallback to footer if newsletter doesn't exist
      this.observer.observe(this.footerSection);
    }
  }

  async waitForPageContent() {
    return new Promise((resolve) => {
      // Check if key content elements are present and loaded
      const checkInterval = setInterval(() => {
        const contentLoaded = this.isPageContentLoaded();
        
        if (contentLoaded) {
          clearInterval(checkInterval);
          // Add a small buffer to ensure smooth transition
          setTimeout(() => {
            resolve();
          }, 100);
        }
      }, 100);

      // Timeout after 3 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        resolve();
      }, 3000);
    });
  }

  isPageContentLoaded() {
    const pathname = window.location.pathname;

    // For home page
    if (pathname === '/') {
      // Check if hero is loaded and either live match or fixtures are present
      const hero = document.querySelector('.hero');
      const liveMatch = document.querySelector('#live-match-section');
      const noMatch = document.querySelector('#no-match-section');
      const fixtures = document.querySelector('.fixtures-section');
      
      return hero && (liveMatch || noMatch || fixtures);
    }

    // For events listing page
    if (pathname === '/events') {
      const eventsContainer = document.getElementById('events-container');
      const skeleton = document.getElementById('events-skeleton');
      const noEventsMsg = document.getElementById('no-events-message');
      
      // Content is loaded when skeleton is hidden and either events or no-events message is shown
      return skeleton && 
             skeleton.style.display === 'none' && 
             (eventsContainer?.style.display !== 'none' || noEventsMsg?.style.display !== 'none');
    }

    // For event detail page
    if (pathname.startsWith('/events/')) {
      const eventContent = document.getElementById('event-content');
      const eventSkeleton = document.getElementById('event-skeleton');
      
      // Content is loaded when skeleton is hidden and content is shown
      return eventSkeleton && 
             eventSkeleton.style.display === 'none' && 
             eventContent?.style.display !== 'none';
    }

    // For matches page
    if (pathname === '/matches') {
      const matchesSection = document.querySelector('.matches-section');
      const resultsSection = document.querySelector('.results-section');
      
      return matchesSection || resultsSection;
    }

    // For join/members/admin pages - simpler check
    if (pathname === '/join' || pathname === '/members' || pathname === '/admin') {
      const pageContent = document.querySelector('#page-content-wrapper');
      const mainSection = document.querySelector('.section');
      
      return pageContent && mainSection;
    }

    // Default: check if main content wrapper exists and has content
    const contentWrapper = document.querySelector('#page-content-wrapper');
    const hasContent = contentWrapper && contentWrapper.children.length > 0;
    
    return hasContent;
  }

  animateFooters() {
    if (this.animated) return;
    
    this.animated = true;

    // Ensure elements are set up
    if (!this.newsletterSection || !this.footerSection) {
      this.setupFooterElements();
    }

    // Trigger animations
    requestAnimationFrame(() => {
      if (this.newsletterSection) {
        this.newsletterSection.classList.add('footer-animated');
      }
      
      if (this.footerSection) {
        this.footerSection.classList.add('footer-animated');
      }
    });

    // Remove will-change after animations complete
    setTimeout(() => {
      if (this.newsletterSection) {
        this.newsletterSection.style.willChange = 'auto';
      }
      if (this.footerSection) {
        this.footerSection.style.willChange = 'auto';
      }
    }, 1500);
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.footerAnimations = new FooterAnimations();
  });
} else {
  window.footerAnimations = new FooterAnimations();
}
