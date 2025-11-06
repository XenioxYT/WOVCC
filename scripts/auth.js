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
        REFRESH_TOKEN: 'wovcc_refresh_token',
        USER: 'wovcc_user'
    };
    const API_BASE = (() => {
        const hostname = window.location.hostname;
        if (!hostname || hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:5000/api';
        }
        return 'https://api.wovcc.co.uk/api';
    })();

    function getAccessToken() {
        return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    }

    function getRefreshToken() {
        return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    }

    function saveAuthData(accessToken, refreshToken, user) {
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    }

    function clearAuthData() {
        localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER);
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
        if (response.status === 401) {
            clearAuthData();
            throw new Error('Session expired. Please login again.');
        }
        return response;
    }
    async function signup(name, email, password, newsletter = false) {
        try {
            try {
                sessionStorage.setItem('wovcc_pending_email', email);
                sessionStorage.setItem('wovcc_pending_password', password);
            } catch (e) {
                debugAuth.warn('Could not store pending credentials:', e);
            }
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
            debugAuth.error('[Auth] Signup error:', error);
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
            debugAuth.error('[Auth]Login error:', error);
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
                    await authenticatedFetch('/auth/logout', {
                        method: 'POST'
                    });
                } catch (e) {}
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
        } else {
            userMenu.classList.remove('show');
            if (adminNavLink) {
                adminNavLink.style.display = 'none';
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
        const needsFreshData = window.location.pathname === '/members' || window.location.pathname === '/admin' || window.location.pathname.startsWith('/join/activate');
        if (isLoggedIn() && needsFreshData) {
            await refreshUserProfile();
            updateNavbar();
        }
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('success') === 'true') {
            debugAuth.log('[Auth]Payment successful,redirecting to activation page');
            window.location.href = '/join/activate';
        } else if (urlParams.get('canceled') === 'true') {
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
        login,
        logout,
        updateNavbar,
        isAdmin,
        refreshUserProfile,
        authenticatedFetch
    };
})();