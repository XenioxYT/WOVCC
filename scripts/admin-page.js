(function() {
  'use strict';

  // Ensure global showNotification is available as a fallback-safe wrapper
  if (!window.showNotification) {
    window.showNotification = function(message, type = 'info') {
      console.log('[' + String(type).toUpperCase() + '] ' + message);
      var mainNotifier = typeof window.showNotification === 'function' && window.showNotification !== arguments.callee;
      if (mainNotifier) {
        try {
          mainNotifier(message, type);
        } catch (e) {
          console.error('Notification error:', e);
        }
      }
    };
  }

  // DOM-based notification implementation used by some admin scripts
  function showDomNotification(message, type) {
    type = type || 'info';

    var existingContainer = document.getElementById('notification-container');
    var container = existingContainer;
    if (!container) {
      container = document.createElement('div');
      container.id = 'notification-container';
      container.className = 'notification-container';
      document.body.appendChild(container);
    }

    var notification = document.createElement('div');
    notification.className = 'notification-toast';
    notification.textContent = message;
    if (type === 'error') {
      notification.classList.add('notification-error');
    } else if (type === 'success') {
      notification.classList.add('notification-success');
    } else if (type === 'warning') {
      notification.classList.add('notification-warning');
    } else {
      notification.classList.add('notification-info');
    }

    container.appendChild(notification);

    // Auto-dismiss with a simple fade effect (CSS-driven)
    setTimeout(function() {
      notification.classList.add('notification-hide');
      setTimeout(function() {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 500);
    }, 3000);
  }

  // Expose DOM notification so existing admin modules can use it if needed
  window.showDomNotification = window.showDomNotification || showDomNotification;

  // Admin page controller logic extracted from inline script in backend/templates/admin.html
  function waitForDependencies(callback, maxAttempts) {
    maxAttempts = typeof maxAttempts === 'number' ? maxAttempts : 50;
    var attempts = 0;
    var interval = setInterval(function() {
      attempts++;
      if (window.WOVCCAuth && window.wovccApi) {
        clearInterval(interval);
        callback();
      } else if (attempts >= maxAttempts) {
        clearInterval(interval);
        console.error('Admin page: Required dependencies not loaded');
        callback();
      }
    }, 100);
  }

  function initAdminPage() {
    waitForDependencies(function() {
      checkAdminAccess();
      setupTabs();
    });
  }

  // Initialize with a small fade-in animation for a smoother experience
  function runAdminInitWithAnimation() {
    var adminContent = document.getElementById('admin-content');
    if (adminContent) {
      // Apply a lightweight fade-in; CSS can refine this using the class.
      adminContent.classList.add('admin-content-transition');
      // Remove the class after animation completes to avoid stacking
      setTimeout(function() {
        adminContent.classList.remove('admin-content-transition');
      }, 300);
    }
    initAdminPage();
  }

  // Initial page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runAdminInitWithAnimation);
  } else {
    runAdminInitWithAnimation();
  }

  // SPA transitions: re-run init (with animation) when navigating to /admin
  document.addEventListener('pageTransitionComplete', function(e) {
    if (e && e.detail && e.detail.path === '/admin') {
      runAdminInitWithAnimation();
    }
  });

  var currentConfig = {};
  var allFixtures = [];
  var tabsInitialized = false; // Track if tabs have been setup to prevent duplicate listeners

  function checkAdminAccess() {
    try {
      if (!window.WOVCCAuth || typeof window.WOVCCAuth.isAdmin !== 'function') {
        console.warn('WOVCCAuth.isAdmin not available yet');
        return;
      }

      var isAdmin = !!window.WOVCCAuth.isAdmin();
      var accessDenied = document.getElementById('access-denied-section');
      var adminContent = document.getElementById('admin-content');

      if (!accessDenied || !adminContent) {
        return;
      }

      // Hide both sections initially to prevent flash
      accessDenied.style.display = 'none';
      adminContent.style.display = 'none';

      if (!isAdmin) {
        accessDenied.style.display = 'block';
        adminContent.style.display = 'none';
      } else {
        accessDenied.style.display = 'none';
        adminContent.style.display = 'block';
        initAdminPanel();
      }

      // Mark auth check as complete to show content
      document.body.classList.add('auth-checked');
    } catch (err) {
      console.error('Error checking admin access:', err);
    }
  }

  function setupTabs() {
    // Prevent duplicate event listeners on SPA transitions
    if (tabsInitialized) return;
    tabsInitialized = true;
    
    var tabs = document.querySelectorAll('.admin-tab');
    if (!tabs || !tabs.length) return;

    tabs.forEach(function(tab) {
      tab.addEventListener('click', function() {
        // Active tab state
        document.querySelectorAll('.admin-tab').forEach(function(t) {
          t.classList.remove('active');
        });
        this.classList.add('active');

        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(function(content) {
          content.style.display = 'none';
        });

        // Show selected
        var tabName = this.getAttribute('data-tab');
        var tabContent = document.getElementById(tabName + '-tab-content');
        if (tabContent) {
          tabContent.style.display = 'block';
        }

        // Trigger events/admin modules as before
        if (tabName === 'dashboard' && window.AdminDashboard && typeof window.AdminDashboard.init === 'function') {
          window.AdminDashboard.init();
        }
        if (tabName === 'events' && window.AdminEvents && typeof window.AdminEvents.loadAdminEvents === 'function') {
          window.AdminEvents.loadAdminEvents();
        }
        if (tabName === 'users' && window.AdminUsers && typeof window.AdminUsers.loadUsers === 'function') {
          // Users script already lazy-loads on tab click; we just ensure tab content is visible
        }
        if (tabName === 'sponsors' && window.AdminSponsors && typeof window.AdminSponsors.loadSponsors === 'function') {
          window.AdminSponsors.loadSponsors();
        }
        if (tabName === 'content' && window.AdminContent && typeof window.AdminContent.loadContentSnippets === 'function') {
          window.AdminContent.loadContentSnippets();
        }
        if (tabName === 'help' && window.AdminHelp && typeof window.AdminHelp.initChat === 'function') {
          window.AdminHelp.initChat();
        }
      });
    });
  }

  async function initAdminPanel() {
    await loadCurrentConfig();
    await loadFixtures();
    setupEventListeners();
    
    // Initialize dashboard since it's the default tab
    if (window.AdminDashboard && typeof window.AdminDashboard.init === 'function') {
      window.AdminDashboard.init();
    }
  }

  async function loadCurrentConfig() {
    try {
      if (!window.wovccApi || !window.wovccApi.baseURL) {
        console.error('wovccApi not available for live-config fetch');
        return;
      }

      var response = await fetch(window.wovccApi.baseURL + '/live-config');
      var data = await response.json();

      if (data && data.success) {
        currentConfig = data.config || {};

        var liveToggle = document.getElementById('live-toggle');
        var livestreamInput = document.getElementById('livestream-url');

        if (liveToggle) {
          liveToggle.checked = !!currentConfig.is_live;
        }
        if (livestreamInput) {
          livestreamInput.value = currentConfig.livestream_url || '';
        }

        updateLiveStatusIndicator(!!currentConfig.is_live);

        if (currentConfig.last_updated) {
          var lastInfo = document.getElementById('last-updated-info');
          var lastTime = document.getElementById('last-updated-time');
          if (lastInfo && lastTime) {
            lastInfo.style.display = 'block';
            lastTime.textContent = new Date(currentConfig.last_updated).toLocaleString();
          }
        }
      }
    } catch (error) {
      console.error('Failed to load config:', error);
      if (typeof window.showNotification === 'function') {
        window.showNotification('Failed to load current configuration', 'error');
      } else {
        showDomNotification('Failed to load current configuration', 'error');
      }
    }
  }

  async function loadFixtures() {
    try {
      if (!window.wovccApi || typeof window.wovccApi.getFixtures !== 'function') {
        console.error('wovccApi.getFixtures not available');
        return;
      }

      var fixtures = await window.wovccApi.getFixtures('all');
      allFixtures = fixtures || [];

      var selector = document.getElementById('match-selector');
      if (!selector) return;

      selector.innerHTML = '<option value="">No match selected</option>';

      allFixtures.forEach(function(fixture, index) {
        var option = document.createElement('option');
        option.value = String(index);
        option.textContent = (
          (fixture.team_name_scraping || '') +
          ' - ' +
          (fixture.home_team || '') +
          ' vs ' +
          (fixture.away_team || '') +
          ' (' +
          (fixture.date_str || fixture.date_iso || '') +
          ')'
        );
        selector.appendChild(option);
      });

      if (currentConfig.selected_match && allFixtures.length) {
        var matchIndex = allFixtures.findIndex(function(f) {
          return (
            f.home_team === currentConfig.selected_match.home_team &&
            f.away_team === currentConfig.selected_match.away_team &&
            f.date_iso === currentConfig.selected_match.date_iso
          );
        });
        if (matchIndex >= 0) {
          selector.value = String(matchIndex);
          showMatchPreview(allFixtures[matchIndex]);
        }
      }
    } catch (error) {
      console.error('Failed to load fixtures:', error);
      if (typeof window.showNotification === 'function') {
        window.showNotification('Failed to load fixtures', 'error');
      } else {
        showDomNotification('Failed to load fixtures', 'error');
      }
    }
  }

  function setupEventListeners() {
    var liveToggle = document.getElementById('live-toggle');
    var matchSelector = document.getElementById('match-selector');
    var saveBtn = document.getElementById('save-config-btn');
    var clearBtn = document.getElementById('clear-config-btn');

    if (liveToggle) {
      liveToggle.addEventListener('change', function(e) {
        updateLiveStatusIndicator(e.target.checked);
      });
    }

    if (matchSelector) {
      matchSelector.addEventListener('change', function(e) {
        var index = e.target.value;
        var preview = document.getElementById('selected-match-preview');
        if (index !== '') {
          var fixture = allFixtures[parseInt(index, 10)];
          if (fixture) {
            showMatchPreview(fixture);
          }
        } else if (preview) {
          preview.style.display = 'none';
        }
      });
    }

    if (saveBtn) {
      saveBtn.addEventListener('click', saveConfiguration);
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', clearConfiguration);
    }
  }

  function updateLiveStatusIndicator(isLive) {
    var indicator = document.getElementById('live-status-indicator');
    var statusText = document.getElementById('status-text');
    if (!indicator || !statusText) return;

    if (isLive) {
      indicator.classList.remove('live-status-inactive');
      indicator.classList.add('live-status-active');
      statusText.innerHTML = '🟢 Live section is <strong>ACTIVE</strong> - Visible to all visitors';
    } else {
      indicator.classList.remove('live-status-active');
      indicator.classList.add('live-status-inactive');
      statusText.innerHTML = '🔴 Live section is <strong>INACTIVE</strong> - Showing regular fixtures/results';
    }
  }

  function showMatchPreview(fixture) {
    var preview = document.getElementById('selected-match-preview');
    var content = document.getElementById('match-preview-content');
    if (!preview || !content || !fixture) return;

    var timeHtml = fixture.time
      ? '<div class="match-preview-row"><strong>Time:</strong> ' + fixture.time + '</div>'
      : '';
    var locationHtml = fixture.location
      ? '<div class="match-preview-row"><strong>Location:</strong> ' + fixture.location + '</div>'
      : '';

    content.innerHTML =
      '<div class="match-preview-container">' +
      '<div class="match-preview-row"><strong>Team:</strong> ' + (fixture.team_name_scraping || '') + '</div>' +
      '<div class="match-preview-row"><strong>Team ID:</strong> ' +
      '<code class="match-preview-code">' +
      (fixture.team_id || '') +
      '</code>' +
      '<span class="match-preview-subtext">(for Play-Cricket widget)</span>' +
      '</div>' +
      '<div class="match-preview-row"><strong>Match:</strong> ' +
      (fixture.home_team || '') +
      ' vs ' +
      (fixture.away_team || '') +
      '</div>' +
      '<div class="match-preview-row"><strong>Date:</strong> ' +
      (fixture.date_str || fixture.date_iso || '') +
      '</div>' +
      timeHtml +
      locationHtml +
      '</div>';

    preview.style.display = 'block';
  }

  async function saveConfiguration() {
    try {
      var liveToggle = document.getElementById('live-toggle');
      var livestreamInput = document.getElementById('livestream-url');
      var matchSelector = document.getElementById('match-selector');

      if (!liveToggle || !livestreamInput || !matchSelector || !window.WOVCCAuth) {
        return;
      }

      var isLive = !!liveToggle.checked;
      var livestreamUrl = (livestreamInput.value || '').trim();
      var matchIndex = matchSelector.value;

      if (isLive && matchIndex === '') {
        (window.showNotification || showDomNotification)(
          'Please select a match when live section is active',
          'warning'
        );
        return;
      }

      var selectedMatch = matchIndex !== '' ? allFixtures[parseInt(matchIndex, 10)] : null;

      var configData = {
        is_live: isLive,
        livestream_url: livestreamUrl,
        selected_match: selectedMatch || null
      };

      var response = await window.WOVCCAuth.authenticatedFetch('/live-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configData)
      });

      var result = await response.json();

      if (result && result.success) {
        currentConfig = result.config || currentConfig;

        var lastInfo = document.getElementById('last-updated-info');
        var lastTime = document.getElementById('last-updated-time');
        if (lastInfo && lastTime && result.config && result.config.last_updated) {
          lastInfo.style.display = 'block';
          lastTime.textContent = new Date(result.config.last_updated).toLocaleString();
        }

        (window.showNotification || showDomNotification)(
          'Configuration saved successfully!',
          'success'
        );
      } else {
        (window.showNotification || showDomNotification)(
          'Failed to save configuration: ' + (result && result.error ? result.error : 'Unknown error'),
          'error'
        );
      }
    } catch (error) {
      console.error('Failed to save config:', error);
      (window.showNotification || showDomNotification)(
        'Failed to save configuration: ' + (error && error.message ? error.message : 'Unknown error'),
        'error'
      );
    }
  }

  async function clearConfiguration() {
    // Use mobile-friendly modal instead of blocking confirm
    const confirmed = await window.WOVCCModal.confirmClear(
      'Are you sure you want to clear all configuration? This will turn off the live section.'
    );
    
    if (!confirmed) {
      return;
    }

    try {
      if (!window.WOVCCAuth) {
        return;
      }

      var configData = {
        is_live: false,
        livestream_url: '',
        selected_match: null
      };

      var response = await window.WOVCCAuth.authenticatedFetch('/live-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configData)
      });

      var result = await response.json();

      if (result && result.success) {
        var liveToggle = document.getElementById('live-toggle');
        var livestreamInput = document.getElementById('livestream-url');
        var matchSelector = document.getElementById('match-selector');
        var preview = document.getElementById('selected-match-preview');

        if (liveToggle) liveToggle.checked = false;
        if (livestreamInput) livestreamInput.value = '';
        if (matchSelector) matchSelector.value = '';
        if (preview) preview.style.display = 'none';

        updateLiveStatusIndicator(false);

        (window.showNotification || showDomNotification)(
          'Configuration cleared successfully!',
          'success'
        );
      } else {
        (window.showNotification || showDomNotification)(
          'Failed to clear configuration: ' + (result && result.error ? result.error : 'Unknown error'),
          'error'
        );
      }
    } catch (error) {
      console.error('Failed to clear config:', error);
      (window.showNotification || showDomNotification)(
        'Failed to clear configuration: ' + (error && error.message ? error.message : 'Unknown error'),
        'error'
      );
    }
  }

  // Export a minimal API if needed later
  window.AdminPage = window.AdminPage || {
    initAdminPage: initAdminPage
  };
})();