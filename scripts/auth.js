// ===================================
// WOVCC Website - Mock Authentication System
// ===================================

// Storage keys
const STORAGE_KEYS = {
  USERS: 'wovcc_users',
  SESSION: 'wovcc_session'
};

// Initialize users array if not exists
function initStorage() {
  if (!localStorage.getItem(STORAGE_KEYS.USERS)) {
    localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify([]));
  }
}

// Get all users from localStorage
function getUsers() {
  initStorage();
  return JSON.parse(localStorage.getItem(STORAGE_KEYS.USERS) || '[]');
}

// Save users to localStorage
function saveUsers(users) {
  localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify(users));
}

// Get current session
function getSession() {
  const session = localStorage.getItem(STORAGE_KEYS.SESSION);
  return session ? JSON.parse(session) : null;
}

// Save session
function saveSession(user) {
  localStorage.setItem(STORAGE_KEYS.SESSION, JSON.stringify(user));
}

// Clear session
function clearSession() {
  localStorage.removeItem(STORAGE_KEYS.SESSION);
}

// Check if user is logged in
function isLoggedIn() {
  return getSession() !== null;
}

// Get current user
function getCurrentUser() {
  return getSession();
}

// Sign up new user
function signup(name, email, password, membershipTier = 'Social Member', newsletter = false) {
  initStorage();
  
  // Validation
  if (!name || !email || !password) {
    return {
      success: false,
      message: 'Please fill in all required fields.'
    };
  }
  
  // Check if email already exists
  const users = getUsers();
  const existingUser = users.find(u => u.email === email);
  
  if (existingUser) {
    return {
      success: false,
      message: 'An account with this email already exists.'
    };
  }
  
  // Create new user
  const newUser = {
    id: Date.now().toString(),
    name: name,
    email: email,
    password: password, // Note: In production, NEVER store plain passwords!
    membershipTier: membershipTier,
    newsletter: newsletter,
    isMember: true,
    joinDate: new Date().toISOString()
  };
  
  // Save user
  users.push(newUser);
  saveUsers(users);
  
  // Auto-login after signup
  const sessionUser = {
    id: newUser.id,
    name: newUser.name,
    email: newUser.email,
    membershipTier: newUser.membershipTier,
    isMember: newUser.isMember
  };
  saveSession(sessionUser);
  
  return {
    success: true,
    message: 'Account created successfully!',
    user: sessionUser
  };
}

// Login user
function login(email, password) {
  if (!email || !password) {
    return {
      success: false,
      message: 'Please enter both email and password.'
    };
  }
  
  const users = getUsers();
  const user = users.find(u => u.email === email && u.password === password);
  
  if (!user) {
    return {
      success: false,
      message: 'Invalid email or password.'
    };
  }
  
  // Create session
  const sessionUser = {
    id: user.id,
    name: user.name,
    email: user.email,
    membershipTier: user.membershipTier,
    isMember: user.isMember
  };
  saveSession(sessionUser);
  
  return {
    success: true,
    message: 'Login successful!',
    user: sessionUser
  };
}

// Logout user
function logout() {
  clearSession();
  return {
    success: true,
    message: 'You have been logged out.'
  };
}

// Check authentication and redirect if needed
function requireAuth() {
  if (!isLoggedIn()) {
    // Show login form instead of redirecting
    return false;
  }
  return true;
}

// Display user info in navbar dropdown
function updateNavbar() {
  const user = getCurrentUser();
  const userMenu = document.getElementById('user-menu');
  const userNameDisplay = document.getElementById('user-name-display');
  
  if (!userMenu) return;
  
  if (user) {
    // Show user dropdown with user's name
    userMenu.classList.add('show');
    if (userNameDisplay) {
      userNameDisplay.textContent = user.name;
    }
  } else {
    // Hide user dropdown
    userMenu.classList.remove('show');
  }
}

// Setup logout button handler
function setupLogoutButton() {
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function(e) {
      e.preventDefault();
      const result = logout();
      if (result.success) {
        updateNavbar();
        // Redirect to home page
        window.location.href = 'index.html';
      }
    });
  }
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', function() {
  initStorage();
  updateNavbar();
  setupLogoutButton();
});

// Export functions for use in other scripts
window.WOVCCAuth = {
  isLoggedIn,
  getCurrentUser,
  signup,
  login,
  logout,
  requireAuth,
  updateNavbar
};

