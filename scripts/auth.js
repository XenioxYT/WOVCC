// ===================================
// WOVCC Website - Authentication System
// Uses backend API with JWT tokens
// ===================================

// Debug utility - only logs in development
const DEBUG = !window.location.hostname || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const debug = {
  log: (...args) => DEBUG && console.log(...args),
  warn: (...args) => DEBUG && console.warn(...args),
  error: (...args) => console.error(...args), // Always log errors
  info: (...args) => DEBUG && console.info(...args)
};

// Storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'wovcc_access_token',
  REFRESH_TOKEN: 'wovcc_refresh_token',
  USER: 'wovcc_user'
};

// API Configuration
// Better API URL detection that handles file:// protocol
const API_BASE = (() => {
  const hostname = window.location.hostname;
  
  // If file:// protocol (empty hostname) or localhost, use local API
  if (!hostname || hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:5000/api';
  }
  
  // Production API
  return 'https://api.wovcc.co.uk/api';
})();

/**
 * Get access token from storage
 */
function getAccessToken() {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

/**
 * Get refresh token from storage
 */
function getRefreshToken() {
  return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
}

/**
 * Save tokens and user data
 */
function saveAuthData(accessToken, refreshToken, user) {
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
  localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
  localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
}

/**
 * Clear auth data
 */
function clearAuthData() {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.USER);
}

/**
 * Get current user from storage
 */
function getCurrentUser() {
  const userStr = localStorage.getItem(STORAGE_KEYS.USER);
  return userStr ? JSON.parse(userStr) : null;
}

/**
 * Check if user is logged in
 */
function isLoggedIn() {
  const token = getAccessToken();
  const user = getCurrentUser();
  return !!(token && user);
}

/**
 * Make authenticated API request
 */
async function authenticatedFetch(endpoint, options = {}) {
  const token = getAccessToken();
  if (!token) {
    throw new Error('No access token available');
  }
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers
  };
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  
  // If token expired, try to refresh
  if (response.status === 401) {
    // For now, just clear and require re-login
    // TODO: Implement token refresh
    clearAuthData();
    throw new Error('Session expired. Please login again.');
  }
  
  return response;
}

/**
 * Register a new user
 */
async function signup(name, email, password, newsletter = false) {
  try {
        // Store credentials temporarily so we can attempt auto-login after successful payment
        try {
          sessionStorage.setItem('wovcc_pending_email', email);
          sessionStorage.setItem('wovcc_pending_password', password);
        } catch (e) {
          // sessionStorage may be unavailable in some contexts; proceed regardless
        }

        // Call pre-register endpoint which creates a pending registration and a Checkout session
        const response = await fetch(`${API_BASE}/auth/pre-register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name,
            email,
            password,
            newsletter
          })
        });

        const data = await response.json();

        if (data.success && data.checkout_url) {
          // The caller will redirect to Stripe Checkout
          return { success: true, checkout_url: data.checkout_url };
        }

        return { success: false, message: data.error || 'Registration failed' };
  } catch (error) {
    return {
      success: false,
      message: error.message || 'Failed to connect to server'
    };
  }
}

/**
 * Login user
 */
async function login(email, password) {
  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email,
        password
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Save tokens and user
      saveAuthData(data.access_token, data.refresh_token, data.user);
      return {
        success: true,
        message: data.message || 'Login successful!',
        user: data.user
      };
    } else {
      return {
        success: false,
        message: data.error || 'Invalid email or password'
      };
    }
  } catch (error) {
    debug.error('[Auth] Login error:', error);
    
    // Check if it's a network error
    if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
      return {
        success: false,
        message: 'Cannot connect to server. Please ensure the API is running.'
      };
    }
    
    return {
      success: false,
      message: error.message || 'Failed to connect to server'
    };
  }
}

/**
 * Logout user
 */
async function logout() {
  try {
    // Try to logout on server (optional, token is invalidated client-side anyway)
    const token = getAccessToken();
    if (token) {
      try {
        await authenticatedFetch('/auth/logout', {
          method: 'POST'
        });
      } catch (e) {
        // Ignore errors on logout
      }
    }
  } finally {
    clearAuthData();
  }
  
  return {
    success: true,
    message: 'You have been logged out.'
  };
}

/**
 * Get user profile from API
 */
async function refreshUserProfile() {
  try {
    const response = await authenticatedFetch('/user/profile');
    const data = await response.json();
    
    if (data.success && data.user) {
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
      return data.user;
    }
    return null;
  } catch (error) {
    debug.error('Failed to refresh user profile:', error);
    return null;
  }
}

/**
 * Check if current user is admin
 */
function isAdmin() {
  const user = getCurrentUser();
  return user && user.is_admin === true;
}

/**
 * Display user info in navbar dropdown
 */
function updateNavbar() {
  const user = getCurrentUser();
  const userMenu = document.getElementById('user-menu');
  const userNameDisplay = document.getElementById('user-name-display');
  const adminNavLink = document.getElementById('admin-nav-link');
  
  if (!userMenu) return;
  
  if (user) {
    // Show user dropdown with user's name
    userMenu.classList.add('show');
    if (userNameDisplay) {
      userNameDisplay.textContent = user.name;
    }
    
    // Show admin link if user is admin
    if (adminNavLink && user.is_admin) {
      adminNavLink.style.display = 'list-item';
    } else if (adminNavLink) {
      adminNavLink.style.display = 'none';
    }
  } else {
    // Hide user dropdown
    userMenu.classList.remove('show');
    
    // Hide admin link
    if (adminNavLink) {
      adminNavLink.style.display = 'none';
    }
  }
}

/**
 * Setup logout button handler
 */
function setupLogoutButton() {
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async function(e) {
      e.preventDefault();
      await logout();
      updateNavbar();
      // Redirect to home page
      window.location.href = 'index.html';
    });
  }
}

/**
 * Create checkout session for payment
 */
async function createCheckoutSession() {
  try {
    const response = await authenticatedFetch('/payments/create-checkout', {
      method: 'POST'
    });
    
    const data = await response.json();
    
    if (data.success && data.checkout_url) {
      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
    } else {
      throw new Error(data.error || 'Failed to create checkout session');
    }
  } catch (error) {
    return {
      success: false,
      message: error.message || 'Failed to create checkout session'
    };
  }
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', async function() {
  // Refresh user profile if logged in
  if (isLoggedIn()) {
    await refreshUserProfile();
  }
  updateNavbar();
  setupLogoutButton();
  
  // Check for payment success/cancel in URL
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('success') === 'true') {
    // Payment successful - try to auto-login using pending credentials stored in sessionStorage
    const pendingEmail = sessionStorage.getItem('wovcc_pending_email');
    const pendingPassword = sessionStorage.getItem('wovcc_pending_password');

    // If user is already logged in, just refresh profile and redirect to members page
    if (isLoggedIn()) {
      await refreshUserProfile();
      updateNavbar();
      if (typeof showNotification === 'function') {
        showNotification('Payment successful! Your membership is now active.', 'success');
      }
      // Redirect to members page
      setTimeout(() => {
        window.location.href = '/pages/members.html';
      }, 1500);
    } else if (pendingEmail && pendingPassword) {
      // FALLBACK: Try to activate account first (for when webhooks don't work in development)
      try {
        debug.log('[Auth] Attempting fallback activation for:', pendingEmail);
        await fetch(`${API_BASE}/auth/check-and-activate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: pendingEmail })
        });
      } catch (e) {
        debug.warn('[Auth] Fallback activation failed, will retry login:', e);
      }
      
      // Attempt to login several times (webhook may take a moment to process)
      let attempts = 0;
      let loggedIn = false;
      while (attempts < 6 && !loggedIn) {
        try {
          const result = await login(pendingEmail, pendingPassword);
          if (result.success) {
            loggedIn = true;
            await refreshUserProfile();
            updateNavbar();
            if (typeof showNotification === 'function') {
              showNotification('Welcome! Redirecting to your membership page...', 'success');
            }
            // Clear pending credentials
            sessionStorage.removeItem('wovcc_pending_email');
            sessionStorage.removeItem('wovcc_pending_password');
            // Redirect to members page
            setTimeout(() => {
              window.location.href = '/pages/members.html';
            }, 1500);
            break;
          }
        } catch (e) {
          // Ignore and retry
        }
        attempts += 1;
        // Wait before retrying
        await new Promise(r => setTimeout(r, 1000));
      }

      if (!loggedIn) {
        // Let the user know their account will be ready; they can login manually
        if (typeof showNotification === 'function') {
          showNotification('Payment successful. Your account has been created — please log in to continue.', 'info');
        }
      }
    }

    // Clean URL
    window.history.replaceState({}, document.title, window.location.pathname);
  } else if (urlParams.get('canceled') === 'true') {
    if (typeof showNotification === 'function') {
      showNotification('Payment was canceled.', 'info');
    }
    // Clean URL
    window.history.replaceState({}, document.title, window.location.pathname);
  }
});

// Export functions for use in other scripts
window.WOVCCAuth = {
  isLoggedIn,
  getCurrentUser,
  signup,
  login,
  logout,
  updateNavbar,
  isAdmin,
  refreshUserProfile,
  authenticatedFetch,
  createCheckoutSession
};

