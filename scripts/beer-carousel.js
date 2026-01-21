/**
 * WOVCC Beer Image Band Handler
 * Handles the beer image band animation and ensures smooth scrolling
 * regardless of the number of images (same approach as sponsor carousel)
 */

(function () {
        'use strict';

        // Store original beer images HTML for proper duplication
        let originalBeerImagesHTML = null;

        /**
         * Initialize the beer image band
         * Handles cases where there are too few images to fill the screen
         */
        function initBeerBand() {
                const wrapper = document.querySelector('.beer-band-wrapper');
                const band = document.querySelector('.beer-band');

                if (!wrapper || !band) return;

                // Store original HTML on first init (before any modifications)
                if (originalBeerImagesHTML === null) {
                        // The template already duplicates images, so we need to get just one set
                        const allLinks = Array.from(band.querySelectorAll('.beer-image-link'));
                        const halfCount = Math.floor(allLinks.length / 2);
                        if (halfCount > 0) {
                                originalBeerImagesHTML = allLinks.slice(0, halfCount).map(el => el.outerHTML).join('');
                        } else {
                                originalBeerImagesHTML = allLinks.map(el => el.outerHTML).join('');
                        }
                }

                // Get the unique image count
                const allLinks = band.querySelectorAll('.beer-image-link');
                const imageCount = Math.floor(allLinks.length / 2) || allLinks.length;

                if (imageCount === 0) return;

                // Wait for images to load to get accurate widths
                const images = band.querySelectorAll('img');
                let loadedCount = 0;
                const totalImages = images.length;

                function checkAndAdjust() {
                        adjustBand(wrapper, band, imageCount);
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
         * Adjust the band based on content width vs viewport width
         */
        function adjustBand(wrapper, band, imageCount) {
                // Get the wrapper width (viewport-like width)
                const wrapperWidth = wrapper.offsetWidth;

                // Calculate the gap from CSS (60px default, 40px on mobile)
                const computedStyle = getComputedStyle(band);
                const gap = parseInt(computedStyle.gap) || 60;

                // Get current image links
                const currentLinks = band.querySelectorAll('.beer-image-link');

                // Calculate width of one set of images
                let singleSetWidth = 0;
                for (let i = 0; i < imageCount && i < currentLinks.length; i++) {
                        singleSetWidth += currentLinks[i].offsetWidth + gap;
                }
                // Subtract one gap (no gap after last item in a set)
                singleSetWidth = Math.max(0, singleSetWidth - gap);

                // Check if we have enough images to fill the screen
                if (singleSetWidth === 0) {
                        // No images, hide the section
                        const container = wrapper.closest('.beer-band-container');
                        if (container) container.style.display = 'none';
                        return;
                }

                // Reset animation to apply fresh calculation
                band.style.animation = 'none';
                // Force reflow to apply the reset
                void band.offsetWidth;

                // If images don't fill the screen width, we need to handle this
                if (singleSetWidth < wrapperWidth) {
                        // Calculate how many complete sets we need to fill at least 2x screen width
                        // (for smooth infinite scroll, we need content width > 2x viewport)
                        const minimumWidth = wrapperWidth * 2.5;
                        const setsNeeded = Math.ceil(minimumWidth / (singleSetWidth + gap));

                        // Rebuild the band with enough duplicates
                        if (originalBeerImagesHTML && setsNeeded > 2) {
                                band.innerHTML = '';
                                for (let i = 0; i < setsNeeded; i++) {
                                        band.insertAdjacentHTML('beforeend', originalBeerImagesHTML);
                                }
                        }

                        // Recalculate after rebuild
                        const newLinks = band.querySelectorAll('.beer-image-link');
                        let totalWidth = 0;
                        for (let i = 0; i < newLinks.length; i++) {
                                totalWidth += newLinks[i].offsetWidth + gap;
                        }
                        totalWidth -= gap;

                        // For very few images (1-2), center them with no animation
                        if (imageCount <= 2) {
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

                                // Apply animation after proper reflow
                                band.style.animation = `scroll-beer ${duration}s linear infinite`;
                        }
                } else {
                        // Normal case - enough images
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

                        // Apply animation immediately (reflow already happened above)
                        band.style.animation = `scroll-beer ${duration}s linear infinite`;
                }
        }

        // Initialize on DOM ready
        if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initBeerBand);
        } else {
                initBeerBand();
        }

        // Re-initialize on SPA page transitions
        document.addEventListener('pageTransitionComplete', () => {
                // Reset stored HTML for fresh page
                originalBeerImagesHTML = null;
                // Small delay to ensure DOM is updated
                setTimeout(initBeerBand, 100);
        });

})();
