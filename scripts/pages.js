/**
 * Centralized page controllers extracted from inline scripts in templates:
 * - members.html
 * - matches.html
 * - join.html
 * - event-detail.html
 * - cancel.html
 * - activate.html
 *
 * Goals:
 * - No inline <script> blocks
 * - No inline event handlers or javascript: URLs
 * - Full compatibility with page-transitions.js (including SPA nav)
 * - Preserve existing behavior as closely as possible
 */
(function() {
  'use strict';

  // Utility: safe showNotification wrapper
  function notify(message, type) {
    if (typeof window.showNotification === 'function') {
      window.showNotification(message, type);
    } else {
      console.log('[' + (type || 'info') + ']', message);
    }
  }

  // Utility: run init when path matches (supports initial load + page transitions)
  function onPage(path, initFn) {
    if (typeof initFn !== 'function') return;

    function runIfMatch() {
      if (
        window.location.pathname === path ||
        (path.endsWith('/') && window.location.pathname.startsWith(path)) ||
        (!path.endsWith('/') && window.location.pathname.startsWith(path + '/'))
      ) {
        initFn();
      }
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', runIfMatch);
    } else {
      runIfMatch();
    }

    document.addEventListener('pageTransitionComplete', function(e) {
      if (e && e.detail && e.detail.path === path) {
        initFn();
      }
    });
  }

  /**
   * MEMBERS PAGE CONTROLLER (/members)
   * Mirrors inline IIFE and onclick="handleLogout()" from members.html
   */
  function initMembersPage() {
    var loginSection = document.getElementById('login-section');
    var membersContent = document.getElementById('members-content');
    var loginForm = document.getElementById('login-form');
    var logoutButton = document.querySelector('#members-content .btn.btn-outline');
    var heroTitle = document.getElementById('members-hero-title');
    var heroSubtitle = document.getElementById('members-hero-subtitle');
    var loginError = document.getElementById('login-error');

    if (!loginSection || !membersContent || !loginForm || !heroTitle || !heroSubtitle) {
      return;
    }
    if (!window.WOVCCAuth) {
      console.warn('[Members] WOVCCAuth not available yet');
      return;
    }

    // Hide both sections initially to prevent flash
    loginSection.style.display = 'none';
    membersContent.style.display = 'none';

    function showLoginForm() {
      loginSection.style.display = 'block';
      membersContent.style.display = 'none';
      heroTitle.textContent = 'Members Area';
      heroSubtitle.textContent = 'Login to access member content';
    }

    function showMembersContent(user) {
      loginSection.style.display = 'none';
      membersContent.style.display = 'block';
      heroTitle.textContent = 'Welcome back, ' + (user.name || 'Member') + '!';
      heroSubtitle.textContent = 'Thank you for being part of WOVCC';
      updateMembershipInfo(user);
    }

    function updateMembershipInfo(user) {
      var membershipTypeEl = document.getElementById('membership-type');
      if (membershipTypeEl && user.membership_tier) {
        membershipTypeEl.textContent = user.membership_tier;
      }

      var statusElement = document.getElementById('membership-status');
      if (statusElement) {
        if (user.payment_status === 'active' && user.is_member) {
          statusElement.textContent = 'Active';
          statusElement.style.color = 'green';
        } else if (user.payment_status === 'expired') {
          statusElement.textContent = 'Expired';
          statusElement.style.color = 'red';
        } else {
          statusElement.textContent = 'Pending';
          statusElement.style.color = 'orange';
        }
      }

      var datesEl = document.getElementById('membership-dates');
      var daysRemainingContainer = document.getElementById('days-remaining-container');
      var daysRemainingEl = document.getElementById('days-remaining');

      if (user.membership_start_date && user.membership_expiry_date && datesEl && daysRemainingContainer && daysRemainingEl) {
        var startDate = new Date(user.membership_start_date);
        var expiryDate = new Date(user.membership_expiry_date);
        var formatOptions = { year: 'numeric', month: 'long', day: 'numeric' };

        var startSpan = document.getElementById('start-date');
        var expirySpan = document.getElementById('expiry-date');
        if (startSpan) startSpan.textContent = startDate.toLocaleDateString('en-GB', formatOptions);
        if (expirySpan) expirySpan.textContent = expiryDate.toLocaleDateString('en-GB', formatOptions);

        var today = new Date();
        var diffMs = expiryDate.getTime() - today.getTime();
        var daysRemaining = Math.ceil(diffMs / (1000 * 3600 * 24));

        if (daysRemaining > 0) {
          daysRemainingEl.textContent = daysRemaining;
          if (daysRemaining <= 30) {
            daysRemainingEl.style.color = 'orange';
          } else {
            daysRemainingEl.style.color = 'var(--accent-color)';
          }
        } else {
          daysRemainingEl.textContent = 'Expired';
          daysRemainingEl.style.color = 'red';
        }

        datesEl.style.display = 'block';
        daysRemainingContainer.style.display = 'block';
      } else {
        if (datesEl) datesEl.style.display = 'none';
        if (daysRemainingContainer) daysRemainingContainer.style.display = 'none';
      }
    }

    function checkAuthStatus() {
      var user = window.WOVCCAuth.getCurrentUser();
      if (user && user.is_member) {
        showMembersContent(user);
      } else {
        showLoginForm();
      }
      // Mark auth check as complete to show content
      document.body.classList.add('auth-checked');
    }

    // Bind login form submit once (avoid duplicates on SPA)
    loginForm.addEventListener('submit', function(e) {
      e.preventDefault();
      if (!window.WOVCCAuth) return;

      var email = document.getElementById('login-email').value;
      var password = document.getElementById('login-password').value;
      var submitBtn = loginForm.querySelector('button[type="submit"]');
      var originalText = submitBtn ? submitBtn.textContent : '';

      if (loginError) {
        loginError.style.display = 'none';
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Logging in...';

      window.WOVCCAuth.login(email, password).then(function(result) {
        if (result && result.success) {
          showMembersContent(result.user);
          window.WOVCCAuth.updateNavbar();
        } else {
          if (loginError) {
            loginError.textContent = (result && result.message) || 'Failed to login. Please try again.';
            loginError.style.display = 'block';
          }
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }).catch(function() {
        if (loginError) {
          loginError.textContent = 'Failed to login. Please try again.';
          loginError.style.display = 'block';
        }
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      });
    }, { once: true });

    // Replace inline handleLogout() with a single bound handler
    function handleLogout() {
      if (!window.WOVCCAuth) return;
      window.WOVCCAuth.logout().then(function() {
        showLoginForm();
        window.WOVCCAuth.updateNavbar();
        window.scrollTo(0, 0);
      });
    }

    if (logoutButton) {
      // Reset any previous handlers to avoid duplicate triggers on SPA transitions
      var newLogoutBtn = logoutButton.cloneNode(true);
      logoutButton.parentNode.replaceChild(newLogoutBtn, logoutButton);
      logoutButton = newLogoutBtn;

      logoutButton.addEventListener('click', function(e) {
        e.preventDefault();
        handleLogout();
      });
    }

    // Only flip visibility once based on current auth state to avoid login→member flicker
    checkAuthStatus();
  }

  // Initialize Members page on direct load and SPA transitions
  if (window.location.pathname === '/members') {
    initMembersPage();
  }
  document.addEventListener('pageTransitionComplete', function(e) {
    if (e && e.detail && e.detail.path === '/members') {
      initMembersPage();
    }
  });

  /**
   * MATCHES PAGE CONTROLLER (/matches)
   * Extracted from inline IIFE; exposes same behavior via script.
   */
  function initMatchesPage() {
    // Ensure API client is ready
    if (!window.wovccApi) {
      console.warn('[Matches] wovccApi not ready');
      return;
    }

    var teamSelector = document.getElementById('team-selector');
    var fixturesTabBtn = document.getElementById('fixtures-tab-btn');
    var resultsTabBtn = document.getElementById('results-tab-btn');
    var fixturesContent = document.getElementById('fixtures-content');
    var resultsContent = document.getElementById('results-content');
    var lastUpdatedContainer = document.getElementById('last-updated-container');

    // If core elements are missing, do nothing (likely not on matches page)
    if (!teamSelector || !fixturesTabBtn || !resultsTabBtn || !fixturesContent || !resultsContent) {
      return;
    }

    // To work with SPA transitions we must allow re-init when navigating back to /matches.
    // So we do not global-lock with _initialized; instead:
    // - Scope state per invocation
    // - Rebind handlers idempotently.
    var currentTeam = 'all';
    var currentTab = 'fixtures';

    function setupTeamSelector() {
      teamSelector.style.opacity = '0.6';
      teamSelector.disabled = true;

      window.wovccApi.getTeams().then(function(teams) {
        teamSelector.innerHTML = '<option value="all">All Teams</option>';
        (teams || []).forEach(function(team) {
          var option = document.createElement('option');
          option.value = team.id;
          option.textContent = team.name;
          teamSelector.appendChild(option);
        });

        // Reset change handler by cloning to avoid duplicate listeners after SPA transitions
        var newSelector = teamSelector.cloneNode(true);
        teamSelector.parentNode.replaceChild(newSelector, teamSelector);
        teamSelector = newSelector;

        teamSelector.addEventListener('change', function() {
          currentTeam = teamSelector.value;
          loadMatchesData();
        });

        teamSelector.style.opacity = '1';
        teamSelector.disabled = false;
      }).catch(function(error) {
        console.error('[Matches] Failed to setup team selector:', error);
        teamSelector.style.opacity = '1';
        teamSelector.disabled = false;
      });
    }

    function switchTab(tab) {
      currentTab = tab;
      [fixturesTabBtn, resultsTabBtn].forEach(function(btn) {
        btn.classList.remove('active');
      });
      if (tab === 'fixtures') {
        fixturesTabBtn.classList.add('active');
      } else {
        resultsTabBtn.classList.add('active');
      }

      [fixturesContent, resultsContent].forEach(function(el) {
        el.classList.remove('active');
      });
      if (tab === 'fixtures') {
        fixturesContent.classList.add('active');
      } else {
        resultsContent.classList.add('active');
      }
    }

    function setupTabs() {
      // Reset existing handlers by cloning to avoid stacking on SPA transitions
      var newFixturesBtn = fixturesTabBtn.cloneNode(true);
      fixturesTabBtn.parentNode.replaceChild(newFixturesBtn, fixturesTabBtn);
      fixturesTabBtn = newFixturesBtn;

      var newResultsBtn = resultsTabBtn.cloneNode(true);
      resultsTabBtn.parentNode.replaceChild(newResultsBtn, resultsTabBtn);
      resultsTabBtn = newResultsBtn;

      fixturesTabBtn.addEventListener('click', function() {
        switchTab('fixtures');
      });
      resultsTabBtn.addEventListener('click', function() {
        switchTab('results');
      });
    }

    function loadFixtures() {
      var container = document.getElementById('fixtures-container');
      if (!container) return;
      window.wovccApi.renderFixturesSkeleton(container, 5);
      window.wovccApi.getFixtures(currentTeam).then(function(fixtures) {
        window.wovccApi.renderFixtures(fixtures, container);
      }).catch(function(error) {
        console.error('[Matches] Failed to load fixtures:', error);
        container.innerHTML =
          '<p style="text-align: center; color: var(--text-light); padding: 40px;">' +
          'Failed to load fixtures. Please try again later.' +
          '</p>';
      });
    }

    function loadResults() {
      var container = document.getElementById('results-container');
      if (!container) return;
      window.wovccApi.renderResultsSkeleton(container, 5);
      window.wovccApi.getResults(currentTeam, 9999).then(function(results) {
        window.wovccApi.renderResults(results, container);
      }).catch(function(error) {
        console.error('[Matches] Failed to load results:', error);
        container.innerHTML =
          '<p style="text-align: center; color: var(--text-light); padding: 40px;">' +
          'Failed to load results. Please try again later.' +
          '</p>';
      });
    }

    function loadMatchesData() {
      Promise.all([loadFixtures(), loadResults()]).then(function() {
        if (lastUpdatedContainer && window.wovccApi.renderLastUpdated) {
          window.wovccApi.renderLastUpdated(lastUpdatedContainer);
        }
      });
    }

    function init() {
      setupTeamSelector();
      setupTabs();
      switchTab(currentTab);
      loadMatchesData();
    }

    init();
  }

  // Ensure matches page initializes on both direct load and SPA transitions,
  // without causing duplicate entrance animations:
  // - We rely on the existing .tab-content CSS animation for the first activation.
  // - Subsequent SPA calls re-run initMatchesPage() but cloning prevents duplicate handlers.
  if (window.location.pathname === '/matches') {
    initMatchesPage();
  }
  document.addEventListener('pageTransitionComplete', function(e) {
    if (e && e.detail && e.detail.path === '/matches') {
      initMatchesPage();
    }
  });

  /**
   * JOIN PAGE CONTROLLER (/join)
   * Extracted from inline IIFE (signup flow).
   */
  function initJoinPage() {
    var form = document.getElementById('signup-form');
    if (!form) return;

    function setupSignupForm() {
      var freshForm = form.cloneNode(true);
      form.parentNode.replaceChild(freshForm, form);
      form = freshForm;

      form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (!window.WOVCCAuth) return;

        var name = document.getElementById('name').value;
        var email = document.getElementById('email').value;
        var password = document.getElementById('password').value;
        var newsletter = document.getElementById('newsletter').checked;

        if (password.length < 6) {
          notify('Password must be at least 6 characters', 'error');
          return;
        }

        var submitBtn = form.querySelector('button[type="submit"]');
        var originalText = submitBtn ? submitBtn.textContent : '';
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Processing...';
        }

        window.WOVCCAuth.signup(name, email, password, newsletter).then(function(result) {
          if (result && result.success && result.checkout_url) {
            window.location.href = result.checkout_url;
          } else {
            notify((result && result.message) || 'Failed to start registration. Please try again.', 'error');
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.textContent = originalText;
            }
          }
        }).catch(function() {
          notify('Failed to connect to server. Please try again.', 'error');
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
          }
        });
      });
    }

    function initJoin() {
      var urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('success') === 'true') {
        window.location.href = '/join/activate';
        return;
      }

      if (urlParams.get('canceled') === 'true') {
        notify('Payment was canceled. Please try again if you\'d like to join.', 'warning');
        window.history.replaceState({}, document.title, window.location.pathname);
      }

      setupSignupForm();
    }

    initJoin();
  }
  onPage('/join', initJoinPage);

  /**
   * EVENT DETAIL PAGE CONTROLLER (/events/<id>)
   * Replaces inline "window.EVENT_ID = {{ event_id }};"
   */
  function initEventDetailPage() {
    // For event detail pages at /events/<id>, derive EVENT_ID from the URL
    var path = window.location.pathname || '';
    var match = path.match(/^\/events\/(\d+)/);
    if (!match) {
      return;
    }
    var id = parseInt(match[1], 10);
    if (!isNaN(id)) {
      window.EVENT_ID = id;
    }
  }

  // Initialize event detail logic whenever navigating under /events
  onPage('/events', function() {
    initEventDetailPage();
  });

  /**
   * CANCEL PAGE CONTROLLER (/join/cancel or similar)
   * Extracted from inline script in cancel.html
   */
  function initCancelPage() {
    var iconContainer = document.getElementById('status-icon');
    var messageContainer = document.getElementById('status-message');
    var actionButton = document.getElementById('action-button');
    if (!iconContainer || !messageContainer || !actionButton) return;

    setTimeout(function() {
      iconContainer.innerHTML =
        '<svg class="cross-icon" viewBox="0 0 100 100">' +
        '<circle cx="50" cy="50" r="45"/>' +
        '<line class="cross-line" x1="30" y1="30" x2="70" y2="70"/>' +
        '<line class="cross-line" x1="70" y1="30" x2="30" y2="70"/>' +
        '</svg>';

      messageContainer.innerHTML =
        '<h2 style="color: #dc3545;">Payment Cancelled</h2>' +
        '<p style="color: #666; margin-top: 15px;">Your payment was cancelled and you have not been charged.</p>' +
        '<p style="color: #666; margin-top: 10px;">No worries! You can try again whenever you\'re ready.</p>';

      actionButton.style.display = 'block';

      try {
        localStorage.removeItem('wovcc_pending_email');
        localStorage.removeItem('wovcc_pending_password');
      } catch (e) {
        console.warn('[Cancel] Failed to clear localStorage', e);
      }
    }, 1500);
  }
  onPage('/join/cancel', initCancelPage);
  onPage('/cancel', initCancelPage);

  /**
   * ACTIVATE PAGE CONTROLLER (/join/activate)
   * Extracted from activate.html inline script.
   */
  function initActivatePage() {
    var statusIcon = document.getElementById('status-icon');
    var statusTitle = document.getElementById('status-title');
    var statusMessage = document.getElementById('status-message');
    var actionsDiv = document.getElementById('actions');
    if (!statusIcon || !statusTitle || !statusMessage || !actionsDiv) return;
    if (!window.WOVCCAuth) {
      console.warn('[Activate] WOVCCAuth not ready');
      return;
    }

    function updateStatus(type, title, message) {
      if (type === 'processing') {
        statusIcon.className = 'status-icon spinner';
        statusIcon.innerHTML = '';
      } else if (type === 'success') {
        statusIcon.className = 'status-icon checkmark';
        statusIcon.innerHTML =
          '<svg viewBox="0 0 52 52">' +
          '<circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>' +
          '<path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>' +
          '</svg>';
      }
      statusTitle.textContent = title;
      statusMessage.textContent = message;
      actionsDiv.style.display = 'none';
    }

    function showTimeout() {
      statusIcon.className = 'status-icon';
      statusIcon.innerHTML =
        '<svg viewBox="0 0 52 52" style="width: 60px; height: 60px;">' +
        '<circle cx="26" cy="26" r="25" fill="none" stroke="#f39c12" stroke-width="2"/>' +
        '<text x="26" y="35" text-anchor="middle" font-size="30" fill="#f39c12">⏱</text>' +
        '</svg>';
      statusTitle.textContent = 'Your account is being created';
      statusMessage.textContent =
        'Your payment was successful! Your account is being set up and should be ready in a few moments.';
      actionsDiv.innerHTML =
        '<a href="/members" class="btn btn-primary">Try Login Now</a>' +
        '<button type="button" class="btn btn-outline" data-action="retry-activation">Retry Activation</button>';
      actionsDiv.style.display = 'flex';

      var retryBtn = actionsDiv.querySelector('[data-action="retry-activation"]');
      if (retryBtn) {
        retryBtn.addEventListener('click', function() {
          window.location.reload();
        });
      }
    }

    function showError() {
      statusIcon.className = 'status-icon';
      statusIcon.innerHTML =
        '<svg viewBox="0 0 52 52" style="width: 60px; height: 60px;">' +
        '<circle cx="26" cy="26" r="25" fill="none" stroke="#e74c3c" stroke-width="2"/>' +
        '<text x="26" y="35" text-anchor="middle" font-size="30" fill="#e74c3c">!</text>' +
        '</svg>';
      statusTitle.textContent = 'No pending registration found';
      statusMessage.textContent = 'Please try logging in or signing up again.';
      actionsDiv.innerHTML =
        '<a href="/members" class="btn btn-primary">Go to Login</a>' +
        '<a href="/join" class="btn btn-outline">Sign Up</a>';
      actionsDiv.style.display = 'flex';
    }

    (async function run() {
      var pendingEmail, pendingPassword;
      try {
        pendingEmail = localStorage.getItem('wovcc_pending_email');
        pendingPassword = localStorage.getItem('wovcc_pending_password');
      } catch (e) {
        console.warn('[Activate] Unable to read localStorage', e);
      }

      if (!pendingEmail || !pendingPassword) {
        showError();
        return;
      }

      updateStatus('processing', 'Creating Your Account', 'Please wait while we set up your membership...');

      var attempts = 0;
      var maxAttempts = 10;

      while (attempts < maxAttempts) {
        attempts++;
        try {
          var result = await window.WOVCCAuth.login(pendingEmail, pendingPassword);
          if (result && result.success) {
            try {
              localStorage.removeItem('wovcc_pending_email');
              localStorage.removeItem('wovcc_pending_password');
            } catch (e) {
              console.warn('[Activate] Unable to clear localStorage', e);
            }

            updateStatus('success', 'Welcome to WOVCC!', 'Your membership is now active. Redirecting to your members area...');
            try {
              await window.WOVCCAuth.refreshUserProfile();
            } catch (e) {
              console.warn('[Activate] Failed to refresh profile', e);
            }
            window.WOVCCAuth.updateNavbar();

            setTimeout(function() {
              window.location.href = '/members';
            }, 2000);
            return;
          }
        } catch (e) {
          console.error('[Activate] Login attempt error:', e);
        }

        if (attempts < maxAttempts) {
          await new Promise(function(resolve) { setTimeout(resolve, 2000); });
        }
      }

      showTimeout();
    })();
  }
  onPage('/join/activate', initActivatePage);

  // 500.html javascript: URL will be fixed in template by switching to a normal button + click listener.
  document.addEventListener('DOMContentLoaded', function() {
    var tryAgainLink = document.querySelector('[data-js-action="reload-page"]');
    if (tryAgainLink) {
      tryAgainLink.addEventListener('click', function(e) {
        e.preventDefault();
        window.location.reload();
      });
    }
  });

  /**
   * CONTACT PAGE CONTROLLER (/contact)
   * Handles contact form submission without inline JS and supports SPA transitions.
   */
  function initContactPage() {
    var form = document.getElementById('contact-form');
    if (!form) return;

    var successBox = document.getElementById('contact-success');
    var errorBox = document.getElementById('contact-error');
    var submitBtn = document.getElementById('contact-submit');

    function showBox(box, message) {
      if (!box) return;
      box.textContent = message;
      box.style.display = 'block';
    }

    function hideBoxes() {
      if (successBox) successBox.style.display = 'none';
      if (errorBox) errorBox.style.display = 'none';
    }

    // Avoid duplicate listeners on SPA transitions by replacing the form node
    var freshForm = form.cloneNode(true);
    form.parentNode.replaceChild(freshForm, form);
    form = freshForm;

    form.addEventListener('submit', function(e) {
      e.preventDefault();
      hideBoxes();

      var name = (document.getElementById('contact-name').value || '').trim();
      var email = (document.getElementById('contact-email').value || '').trim();
      var subject = (document.getElementById('contact-subject').value || '').trim();
      var message = (document.getElementById('contact-message').value || '').trim();

      if (!name || !email || !subject || !message) {
        showBox(errorBox, 'Please complete all required fields.');
        return;
      }

      var payload = {
        name: name,
        email: email,
        subject: subject,
        message: message
      };

      var originalText = submitBtn ? submitBtn.textContent : '';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';
      }

      fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })
        .then(function(res) {
          return res.json().catch(function() { return {}; }).then(function(data) {
            return { res: res, data: data };
          });
        })
        .then(function(result) {
          var res = result.res;
          var data = result.data || {};
          if (res.ok && data.success) {
            form.reset();
            showBox(successBox, 'Your message has been sent successfully.');
          } else {
            var msg =
              data.error ||
              data.message ||
              'Something went wrong sending your message. Please try again.';
            showBox(errorBox, msg);
          }
        })
        .catch(function(err) {
          console.error('Contact form error:', err);
          showBox(errorBox, 'Network error sending message. Please try again.');
        })
        .finally(function() {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
          }
        });
    });
  }

  // Wire contact page for direct load and SPA transitions
  onPage('/contact', initContactPage);
})();