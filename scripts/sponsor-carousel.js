/**
 * WOVCC Sponsor Carousel Handler
 * Handles the sponsor band animation and ensures smooth scrolling
 * regardless of the number of sponsors
 */

(function() {
  'use strict';

  // Store original sponsor HTML for proper duplication
  let originalSponsorsHTML = null;

  /**
   * Initialize the sponsor carousel
   * Handles cases where there are too few sponsors to fill the screen
   */
  function initSponsorCarousel() {
    const wrapper = document.querySelector('.sponsors-band-wrapper');
    const band = document.querySelector('.sponsors-band');
    
    if (!wrapper || !band) return;
    
    // Store original HTML on first init (before any modifications)
    if (originalSponsorsHTML === null) {
      // The template already duplicates sponsors, so we need to get just one set
      const allLinks = Array.from(band.querySelectorAll('.sponsor-logo-link'));
      const halfCount = Math.floor(allLinks.length / 2);
      if (halfCount > 0) {
        originalSponsorsHTML = allLinks.slice(0, halfCount).map(el => el.outerHTML).join('');
      } else {
        originalSponsorsHTML = allLinks.map(el => el.outerHTML).join('');
      }
    }
    
    // Get the unique sponsor count
    const allLinks = band.querySelectorAll('.sponsor-logo-link');
    const sponsorCount = Math.floor(allLinks.length / 2) || allLinks.length;
    
    if (sponsorCount === 0) return;
    
    // Wait for images to load to get accurate widths
    const images = band.querySelectorAll('img');
    let loadedCount = 0;
    const totalImages = images.length;
    
    function checkAndAdjust() {
      adjustCarousel(wrapper, band, sponsorCount);
    }
    
    // Check if all images are already loaded
    let allLoaded = true;
    images.forEach(img => {
      if (!img.complete) {
        allLoaded = false;
        img.addEventListener('load', () => {
          loadedCount++;
          if (loadedCount >= totalImages) {
            checkAndAdjust();
          }
        }, { once: true });
        img.addEventListener('error', () => {
          loadedCount++;
          if (loadedCount >= totalImages) {
            checkAndAdjust();
          }
        }, { once: true });
      }
    });
    
    if (allLoaded) {
      // Small delay to ensure layout is complete
      setTimeout(checkAndAdjust, 100);
    }
    
    // Also adjust on window resize (debounced)
    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(checkAndAdjust, 200);
    });
  }

  /**
   * Adjust the carousel based on content width vs viewport width
   */
  function adjustCarousel(wrapper, band, sponsorCount) {
    // Get the wrapper width (viewport-like width)
    const wrapperWidth = wrapper.offsetWidth;
    
    // Calculate the gap from CSS (60px default, 40px on mobile)
    const computedStyle = getComputedStyle(band);
    const gap = parseInt(computedStyle.gap) || 60;
    
    // Get current sponsor links
    const currentLinks = band.querySelectorAll('.sponsor-logo-link');
    
    // Calculate width of one set of sponsors
    let singleSetWidth = 0;
    for (let i = 0; i < sponsorCount && i < currentLinks.length; i++) {
      singleSetWidth += currentLinks[i].offsetWidth + gap;
    }
    // Subtract one gap (no gap after last item in a set)
    singleSetWidth = Math.max(0, singleSetWidth - gap);
    
    // Check if we have enough sponsors to fill the screen
    if (singleSetWidth === 0) {
      // No sponsors, hide the section
      const container = wrapper.closest('.sponsors-band-container');
      if (container) container.style.display = 'none';
      return;
    }
    
    // Reset animation to apply fresh calculation
    band.style.animation = 'none';
    band.style.transform = '';
    
    // If sponsors don't fill the screen width, we need to handle this
    if (singleSetWidth < wrapperWidth) {
      // Calculate how many complete sets we need to fill at least 2x screen width
      // (for smooth infinite scroll, we need content width > 2x viewport)
      const minimumWidth = wrapperWidth * 2.5;
      const setsNeeded = Math.ceil(minimumWidth / (singleSetWidth + gap));
      
      // Rebuild the band with enough duplicates
      if (originalSponsorsHTML && setsNeeded > 2) {
        band.innerHTML = '';
        for (let i = 0; i < setsNeeded; i++) {
          band.insertAdjacentHTML('beforeend', originalSponsorsHTML);
        }
      }
      
      // Recalculate after rebuild
      const newLinks = band.querySelectorAll('.sponsor-logo-link');
      let totalWidth = 0;
      for (let i = 0; i < newLinks.length; i++) {
        totalWidth += newLinks[i].offsetWidth + gap;
      }
      totalWidth -= gap;
      
      // For very few sponsors (1-2), center them with no animation
      if (sponsorCount <= 2) {
        band.style.justifyContent = 'center';
        band.style.width = 'auto';
        band.style.animation = 'none';
      } else {
        band.style.justifyContent = 'flex-start';
        band.style.width = 'max-content';
        
        // Calculate animation duration based on content width
        // Slower for less content to prevent fast/snappy feel
        const pixelsPerSecond = 40; // Consistent scroll speed
        const halfWidth = totalWidth / 2;
        const duration = Math.max(15, halfWidth / pixelsPerSecond);
        
        // Apply animation after a reflow
        requestAnimationFrame(() => {
          band.style.animation = `scroll-sponsors ${duration}s linear infinite`;
        });
      }
    } else {
      // Normal case - enough sponsors
      band.style.justifyContent = 'flex-start';
      band.style.width = 'max-content';
      
      // Get total width with current duplication
      let totalWidth = 0;
      for (let i = 0; i < currentLinks.length; i++) {
        totalWidth += currentLinks[i].offsetWidth + gap;
      }
      totalWidth -= gap;
      
      // Calculate duration for consistent scroll speed
      const pixelsPerSecond = 50;
      const halfWidth = totalWidth / 2;
      const duration = Math.max(20, halfWidth / pixelsPerSecond);
      
      requestAnimationFrame(() => {
        band.style.animation = `scroll-sponsors ${duration}s linear infinite`;
      });
    }
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSponsorCarousel);
  } else {
    initSponsorCarousel();
  }

  // Re-initialize on SPA page transitions
  document.addEventListener('pageTransitionComplete', () => {
    // Small delay to ensure DOM is updated
    setTimeout(initSponsorCarousel, 100);
  });

})();
