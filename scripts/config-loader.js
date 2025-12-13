/**
 * Config Loader
 * Reads application configuration from a JSON script tag and exposes it as window.APP_CONFIG.
 * This approach avoids inline script execution, which is blocked by CSP.
 */
(function() {
    'use strict';
    
    // Only initialize once
    if (window.APP_CONFIG) {
        return;
    }
    
    try {
        var configElement = document.getElementById('app-config-data');
        if (configElement && configElement.textContent) {
            window.APP_CONFIG = JSON.parse(configElement.textContent.trim());
        } else {
            // Fallback defaults if config element is not found
            console.warn('[ConfigLoader] Config element not found, using defaults');
            window.APP_CONFIG = {
                apiBase: '/api',
                siteBase: '',
                isDebug: false,
                environment: 'production'
            };
        }
    } catch (e) {
        console.error('[ConfigLoader] Failed to parse config:', e);
        // Fallback defaults on error
        window.APP_CONFIG = {
            apiBase: '/api',
            siteBase: '',
            isDebug: false,
            environment: 'production'
        };
    }
})();

