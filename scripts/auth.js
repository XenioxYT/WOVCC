(function() {
    'use strict';
    const DEBUG_AUTH = !window.location.hostname || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const debugAuth = {
        log: (...args) => DEBUG_AUTH && console.log(...args),
        warn: (...args) => DEBUG_AUTH && console.warn(...args),
        error: (...args) => console.error(...args),
        info: (...args) => DEBUG_AUTH && console.info(...args)
    };
    const STORAGE_KEYS = {
        ACCESS_TOKEN: 'wovcc_access_token',
        USER: 'wovcc_user'
    };
    const API_BASE = (() => {
        const hostname = window.location.hostname;
        if (!hostname || hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:5000/api';
        }
        return 'https://wovcc.xeniox.uk/api';
    })();

    function getAccessToken() {
        return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    }

    function saveAuthData(accessToken, user) {
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    }

    function clearAuthData() {
        localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER);
        // Note: Refresh token is stored as httpOnly cookie and will be cleared by server
    }

    function getCurrentUser() {
        const userStr = localStorage.getItem(STORAGE_KEYS.USER);
        return userStr ? JSON.parse(userStr) : null;
    }

    function isLoggedIn() {
        const token = getAccessToken();
        const user = getCurrentUser();
        return !!(token && user);
    }

    async function refreshAccessToken() {
        try {
            const response = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                credentials: 'include', // Include cookies
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                debugAuth.error('Token refresh failed with status:', response.status);
                return null;
            }
            const data = await response.json();
            
            if (data.success && data.access_token) {
                localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
                return data.access_token;
            }
            
            return null;
        } catch (error) {
            debugAuth.error('Token refresh failed:', error);
            return null;
        }
    }

    async function authenticatedFetch(endpoint, options = {}) {
        const doFetch = async (token) => {
            if (!token) {
                throw new Error('No access token available');
            }
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...options.headers
            };
            return fetch(`${API_BASE}${endpoint}`, {
                ...options,
                credentials: 'include',
                headers
            });
        };

        let response = await doFetch(getAccessToken());

        if (response.status === 401) {
            debugAuth.info('Access token expired, attempting refresh...');
            const newToken = await refreshAccessToken();
            
            if (newToken) {
                // Retry the original request with new token
                return doFetch(newToken);
            }
            
            // Refresh failed, clear auth data
            clearAuthData();
            throw new Error('Session expired. Please login again.');
        }
        
        return response;
    }
    async function signup(name, email, password, newsletter = false, includeSpouseCard = false) {
        try {
            // SECURITY: Do NOT store password in localStorage
            // The activation token passed via URL after payment is used for secure activation
            
            const response = await fetch(`${API_BASE}/auth/pre-register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    email,
                    password,
                    newsletter,
                    includeSpouseCard
                })
            });
            
            const data = await response.json();
            if (data.success && data.checkout_url) {
                return {
                    success: true,
                    checkout_url: data.checkout_url,
                    pending_id: data.pending_id
                };
            }
            return {
                success: false,
                message: data.error || 'Registration failed'
            };
        } catch (error) {
            debugAuth.error('Signup error:', error);
            return {
                success: false,
                message: error.message || 'Failed to connect to server'
            };
        }
    }
    async function activate(activationToken) {
        try {
            const response = await fetch(`${API_BASE}/auth/activate`, {
                method: 'POST',
                credentials: 'include', // Include cookies for refresh token
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    activation_token: activationToken
                })
            });
            
            const data = await response.json();
            
            if (response.status === 202 && data.status === 'pending') {
                // Account still being created
                return {
                    success: false,
                    status: 'pending',
                    message: data.message || 'Account being created...'
                };
            }
            
            if (data.success) {
                // Account activated successfully, save auth data
                saveAuthData(data.access_token, data.user);
                return {
                    success: true,
                    message: data.message || 'Account activated!',
                    user: data.user
                };
            } else {
                return {
                    success: false,
                    status: data.status,
                    message: data.error || data.message || 'Activation failed'
                };
            }
        } catch (error) {
            debugAuth.error('Activation error:', error);
            return {
                success: false,
                message: error.message || 'Failed to connect to server'
            };
        }
    }
    
    async function login(email, password) {
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                credentials: 'include', // Include cookies for refresh token
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
                // Only save access token and user (refresh token is in httpOnly cookie)
                saveAuthData(data.access_token, data.user);
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
            debugAuth.error('Login error:', error);
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
    async function logout() {
        try {
            const token = getAccessToken();
            if (token) {
                try {
                    // This will clear the httpOnly cookie on the server
                    await authenticatedFetch('/auth/logout', {
                        method: 'POST'
                    });
                } catch (e) {
                    debugAuth.warn('Logout request failed:', e);
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
            debugAuth.error('Failed to refresh user profile:', error);
            return null;
        }
    }

    function isAdmin() {
        const user = getCurrentUser();
        return user && user.is_admin === true;
    }

    function updateNavbar() {
        const user = getCurrentUser();
        const userMenu = document.getElementById('user-menu');
        const userNameDisplay = document.getElementById('user-name-display');
        const adminNavLink = document.getElementById('admin-nav-link');
        const joinNavLinks = document.querySelectorAll('.nav-link[href="/join"]');
        const loginNavLink = document.getElementById('login-nav-link');
        const membershipNavLink = document.getElementById('membership-nav-link');
        
        if (!userMenu) return;
        
        if (user) {
            userMenu.classList.add('show');
            if (userNameDisplay) {
                userNameDisplay.textContent = user.name;
            }
            if (adminNavLink && user.is_admin) {
                adminNavLink.style.display = 'list-item';
            } else if (adminNavLink) {
                adminNavLink.style.display = 'none';
            }
            // Hide Join and Login buttons when logged in
            joinNavLinks.forEach(link => {
                const listItem = link.parentElement;
                if (listItem) {
                    listItem.style.display = 'none';
                }
            });
            if (loginNavLink) {
                loginNavLink.style.display = 'none';
            }
            // Show Membership link when logged in
            if (membershipNavLink) {
                membershipNavLink.style.display = 'list-item';
            }
        } else {
            userMenu.classList.remove('show');
            if (adminNavLink) {
                adminNavLink.style.display = 'none';
            }
            // Show Join and Login buttons when not logged in
            joinNavLinks.forEach(link => {
                const listItem = link.parentElement;
                if (listItem) {
                    listItem.style.display = 'list-item';
                }
            });
            if (loginNavLink) {
                loginNavLink.style.display = 'list-item';
            }
            // Hide Membership link when not logged in
            if (membershipNavLink) {
                membershipNavLink.style.display = 'none';
            }
        }
    }

    function setupLogoutButton() {
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async function(e) {
                e.preventDefault();
                await logout();
                window.location.href = '/';
            });
        }
    }
    document.addEventListener('DOMContentLoaded', async function() {
        updateNavbar();
        setupLogoutButton();
        const needsFreshData = window.location.pathname === '/members' || window.location.pathname === '/membership' || window.location.pathname === '/admin' || window.location.pathname.startsWith('/join/activate');
        if (isLoggedIn() && needsFreshData) {
            await refreshUserProfile();
            updateNavbar();
        }
        // Note: Stripe redirect handling removed - success URL now goes directly to /join/activate?token=...
        // The activate page handles the secure token-based activation
        const urlParams = new URLSearchParams(window.location.search);
        
        if (urlParams.get('canceled') === 'true') {
            if (typeof showNotification === 'function') {
                showNotification('Payment was canceled.', 'info');
            }
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    });
    window.WOVCCAuth = {
        isLoggedIn,
        getCurrentUser,
        signup,
        activate,
        login,
        logout,
        updateNavbar,
        isAdmin,
        refreshUserProfile,
        authenticatedFetch
    };
})();