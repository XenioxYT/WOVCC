(function() {
    'use strict';
    
    
    let allUsers = [];
    let currentPage = 1;
    let currentFilter = 'all';
    let currentSearch = '';
    let currentSort = 'join_date';
    let currentOrder = 'desc';
    let currentEditingUser = null;
    let stats = null;
    let isInitialized = false;
    
    // Initialize function to be called when users tab becomes active
    function initializeUsersTab() {
        console.log('Initializing users tab, isInitialized:', isInitialized);
        if (!isInitialized) {
            isInitialized = true;
            console.log('Loading admin stats and users...');
            loadAdminStats();
            loadAdminUsers();
        } else {
            console.log('Users tab already initialized');
        }
    }
    
    // Initialize when the users tab is clicked - supports both initial load and page transitions
    function setupUsersTabListener() {
        const usersTab = document.getElementById('users-tab');
        if (usersTab) {
            console.log('Setting up users tab click listener');
            // Remove any existing listener to avoid duplicates
            usersTab.removeEventListener('click', initializeUsersTab);
            usersTab.addEventListener('click', function() {
                console.log('Users tab clicked');
                initializeUsersTab();
            });
        } else {
            console.warn('Users tab element not found');
        }
    }
    
    // Setup on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupUsersTabListener);
    } else {
        setupUsersTabListener();
    }
    
    // Also setup on page transitions
    document.addEventListener('pageTransitionComplete', function(e) {
        if (e.detail && e.detail.path === '/admin') {
            isInitialized = false; // Reset initialization flag
            setupUsersTabListener();
        }
    });
    
    async function loadAdminStats() {
        try {
            if (!window.WOVCCAuth || !window.WOVCCAuth.authenticatedFetch) {
                console.error('WOVCCAuth not available');
                return;
            }
            
            const response = await window.WOVCCAuth.authenticatedFetch('/admin/stats');
            const data = await response.json();
            
            if (data.success) {
                stats = data.stats;
                renderStatsCards(stats);
            } else {
                console.error('Failed to load stats:', data.error);
            }
        } catch (error) {
            console.error('Failed to load admin stats:', error);
        }
    }
    
    function renderStatsCards(stats) {
        const container = document.getElementById('admin-stats-cards');
        if (!container) {
            console.warn('Stats cards container not found');
            return;
        }
        
        if (!stats) {
            console.warn('No stats data to render');
            return;
        }
        
        const activePercentage = stats.total_members > 0 
            ? ((stats.active_members / stats.total_members) * 100).toFixed(1) 
            : 0;
        
        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon" style="background: #e3f2fd; color: #1976d2;">
                        <svg fill="currentColor" viewBox="0 0 20 20" style="width: 24px; height: 24px;">
                            <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/>
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-label">Total Members</div>
                        <div class="stat-value">${stats.total_members}</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: #e8f5e9; color: #388e3c;">
                        <svg fill="currentColor" viewBox="0 0 20 20" style="width: 24px; height: 24px;">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-label">Active Members</div>
                        <div class="stat-value">${stats.active_members}</div>
                        <div class="stat-subtitle">${activePercentage}% of total</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: #fff3e0; color: #f57c00;">
                        <svg fill="currentColor" viewBox="0 0 20 20" style="width: 24px; height: 24px;">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-label">Expiring Soon</div>
                        <div class="stat-value">${stats.expiring_soon}</div>
                        <div class="stat-subtitle">Within 30 days</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: #f3e5f5; color: #7b1fa2;">
                        <svg fill="currentColor" viewBox="0 0 20 20" style="width: 24px; height: 24px;">
                            <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-label">New This Month</div>
                        <div class="stat-value">${stats.new_members_this_month}</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: #fce4ec; color: #c2185b;">
                        <svg fill="currentColor" viewBox="0 0 20 20" style="width: 24px; height: 24px;">
                            <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z"/>
                            <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z"/>
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-label">Newsletter Subscribers</div>
                        <div class="stat-value">${stats.newsletter_subscribers}</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: #ffebee; color: #c62828;">
                        <svg fill="currentColor" viewBox="0 0 20 20" style="width: 24px; height: 24px;">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-label">Expired Members</div>
                        <div class="stat-value">${stats.expired_members}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    async function loadAdminUsers(page = 1) {
        try {
            if (!window.WOVCCAuth || !window.WOVCCAuth.authenticatedFetch) {
                console.error('WOVCCAuth not available');
                showUsersError('Authentication system not loaded');
                return;
            }
            
            showUsersLoading();
            currentPage = page;
            
            const params = new URLSearchParams({
                page: currentPage,
                per_page: 50,
                filter: currentFilter,
                sort: currentSort,
                order: currentOrder
            });
            
            if (currentSearch) {
                params.append('search', currentSearch);
            }
            
            const response = await window.WOVCCAuth.authenticatedFetch(`/admin/users?${params}`);
            const data = await response.json();
            
            if (data.success) {
                allUsers = data.users;
                renderUsersTable(allUsers, data.pagination);
            } else {
                showUsersError('Failed to load users: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Failed to load users:', error);
            showUsersError(error.message || 'Failed to load users');
        }
    }
    
    function renderUsersTable(users, pagination) {
        const container = document.getElementById('admin-users-list');
        if (!container) return;
        
        if (!users || users.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-light);">
                    <p>No users found.</p>
                </div>
            `;
            return;
        }
        
        const tableHTML = `
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--secondary-bg); border-bottom: 2px solid var(--border-color);">
                            <th
                              style="padding: 12px; text-align: left; font-weight: 600; cursor: pointer;"
                              data-admin-users-sort="name"
                            >
                                Name ${getSortIndicator('name')}
                            </th>
                            <th
                              style="padding: 12px; text-align: left; font-weight: 600; cursor: pointer;"
                              data-admin-users-sort="email"
                            >
                                Email ${getSortIndicator('email')}
                            </th>
                            <th style="padding: 12px; text-align: center; font-weight: 600;">Status</th>
                            <th
                              style="padding: 12px; text-align: center; font-weight: 600; cursor: pointer;"
                              data-admin-users-sort="join_date"
                            >
                                Join Date ${getSortIndicator('join_date')}
                            </th>
                            <th
                              style="padding: 12px; text-align: center; font-weight: 600; cursor: pointer;"
                              data-admin-users-sort="expiry_date"
                            >
                                Expiry ${getSortIndicator('expiry_date')}
                            </th>
                            <th style="padding: 12px; text-align: center; font-weight: 600;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${users.map(user => createUserRow(user)).join('')}
                    </tbody>
                </table>
            </div>
            ${renderPagination(pagination)}
        `;
        
        container.innerHTML = tableHTML;
        
        // Attach event listeners for user actions
        users.forEach(user => {
            const editBtn = document.getElementById(`edit-user-${user.id}`);
            const deleteBtn = document.getElementById(`delete-user-${user.id}`);
            
            if (editBtn) editBtn.addEventListener('click', () => openEditUserModal(user));
            if (deleteBtn) deleteBtn.addEventListener('click', () => deleteUser(user.id, user.name));
        });
        
        // Attach event listeners for pagination buttons (CSP-compliant)
        const paginationBtns = container.querySelectorAll('.pagination-btn');
        paginationBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.getAttribute('data-page'), 10);
                if (page && window.AdminUsers && window.AdminUsers.loadUsers) {
                    window.AdminUsers.loadUsers(page);
                }
            });
        });
    }
    
    function getSortIndicator(field) {
        if (currentSort !== field) return '';
        return currentOrder === 'asc' ? '↑' : '↓';
    }
    
    function createUserRow(user) {
        // Security: Use escapeHtml to prevent XSS attacks
        const escapeHtml = window.HTMLSanitizer ? window.HTMLSanitizer.escapeHtml : (str => String(str));
        
        const memberBadge = user.is_member 
            ? '<span style="background: #d4edda; color: #155724; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">Member</span>'
            : '<span style="background: #f8d7da; color: #721c24; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">Non-Member</span>';
        
        const adminBadge = user.is_admin 
            ? '<span style="background: #1a5f5f; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; margin-left: 5px;">Admin</span>'
            : '';
        
        const paymentStatus = escapeHtml(user.payment_status || 'N/A');
        const paymentBadgeColor = {
            'active': '#d4edda',
            'pending': '#fff3cd',
            'expired': '#f8d7da',
            'cancelled': '#f8d7da'
        }[user.payment_status] || '#e2e3e5';
        
        const paymentBadgeText = {
            'active': '#155724',
            'pending': '#856404',
            'expired': '#721c24',
            'cancelled': '#721c24'
        }[user.payment_status] || '#383d41';
        
        const joinDate = user.join_date ? new Date(user.join_date).toLocaleDateString('en-GB') : 'N/A';
        const expiryDate = user.membership_expiry_date ? new Date(user.membership_expiry_date).toLocaleDateString('en-GB') : 'N/A';
        
        // Check if expired
        const isExpired = user.membership_expiry_date && new Date(user.membership_expiry_date) < new Date();
        const expiryColor = isExpired ? 'color: var(--accent-color); font-weight: 600;' : '';
        
        // Escape all user-provided data
        const safeName = escapeHtml(user.name);
        const safeEmail = escapeHtml(user.email);
        const safeTier = escapeHtml(user.membership_tier || 'N/A');
        const safeUserId = parseInt(user.id, 10); // Ensure ID is a number
        
        return `
            <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: 12px;">
                    <div style="font-weight: 600; color: var(--text-dark); margin-bottom: 4px;">${safeName}</div>
                    <div style="font-size: 0.85rem; color: var(--text-light);">${safeTier}</div>
                </td>
                <td style="padding: 12px;">${safeEmail}</td>
                <td style="padding: 12px; text-align: center;">
                    ${memberBadge}${adminBadge}
                    <div style="margin-top: 5px;">
                        <span style="background: ${paymentBadgeColor}; color: ${paymentBadgeText}; padding: 2px 8px; border-radius: 8px; font-size: 0.75rem; font-weight: 600;">
                            ${paymentStatus}
                        </span>
                    </div>
                </td>
                <td style="padding: 12px; text-align: center; white-space: nowrap;">${joinDate}</td>
                <td style="padding: 12px; text-align: center; white-space: nowrap; ${expiryColor}">${expiryDate}</td>
                <td style="padding: 12px; text-align: center;">
                    <div style="display: flex; gap: 10px; justify-content: center;">
                        <button id="edit-user-${safeUserId}" class="btn-icon" title="Edit User">
                            <svg fill="currentColor" viewBox="0 0 20 20">
                                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
                            </svg>
                        </button>
                        <button id="delete-user-${safeUserId}" class="btn-icon btn-icon-danger" title="Delete User">
                            <svg fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    function renderPagination(pagination) {
        if (!pagination || pagination.pages <= 1) return '';
        
        let html = '<div class="pagination-container" style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border-color);">';
        
        // Previous button
        if (pagination.page > 1) {
            html += `<button class="pagination-btn" data-page="${pagination.page - 1}" class="btn btn-outline" style="padding: 8px 16px;">Previous</button>`;
        }
        
        // Page info
        html += `<span style="color: var(--text-light);">Page ${pagination.page} of ${pagination.pages} (${pagination.total} total)</span>`;
        
        // Next button
        if (pagination.page < pagination.pages) {
            html += `<button class="pagination-btn" data-page="${pagination.page + 1}" class="btn btn-outline" style="padding: 8px 16px;">Next</button>`;
        }
        
        html += '</div>';
        return html;
    }
    
    function showUsersLoading() {
        const container = document.getElementById('admin-users-list');
        if (!container) return;
        
        container.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <div class="skeleton-spinner"></div>
                <p style="margin-top: 15px; color: var(--text-light);">Loading users...</p>
            </div>
        `;
    }
    
    function showUsersError(message) {
        const container = document.getElementById('admin-users-list');
        if (!container) return;
        
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--accent-color);">
                <p>${message}</p>
            </div>
        `;
    }
    
    function applyFilter(filter) {
        currentFilter = filter;
        currentPage = 1;
        loadAdminUsers(1);
        
        // Update filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-admin-users-filter="${filter}"]`)?.classList.add('active');
    }
    
    function applySearch(searchTerm) {
        currentSearch = searchTerm;
        currentPage = 1;
        loadAdminUsers(1);
    }
    
    function sortBy(field) {
        if (currentSort === field) {
            currentOrder = currentOrder === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort = field;
            currentOrder = 'desc';
        }
        loadAdminUsers(currentPage);
    }
    
    function openEditUserModal(user) {
        currentEditingUser = user;
        const modal = document.getElementById('user-modal');
        if (!modal) return;
        
        document.getElementById('user-name').value = user.name;
        document.getElementById('user-email').value = user.email;
        document.getElementById('user-is-member').checked = user.is_member;
        document.getElementById('user-is-admin').checked = user.is_admin;
        document.getElementById('user-newsletter').checked = user.newsletter;
        document.getElementById('user-payment-status').value = user.payment_status || 'pending';
        document.getElementById('user-membership-tier').value = user.membership_tier || 'Annual Member';
        document.getElementById('user-expiry-date').value = user.membership_expiry_date 
            ? new Date(user.membership_expiry_date).toISOString().slice(0, 10)
            : '';
        
        document.getElementById('user-modal-title').textContent = `Edit User: ${user.name}`;
        document.getElementById('user-submit-btn').textContent = 'Update User';
        
        modal.style.display = 'flex';
    }
    
    function closeUserModal() {
        const modal = document.getElementById('user-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        currentEditingUser = null;
    }
    
    async function handleUserSubmit(e) {
        e.preventDefault();
        
        if (!currentEditingUser) return;
        
        const data = {
            name: document.getElementById('user-name').value,
            email: document.getElementById('user-email').value,
            is_member: document.getElementById('user-is-member').checked,
            is_admin: document.getElementById('user-is-admin').checked,
            newsletter: document.getElementById('user-newsletter').checked,
            payment_status: document.getElementById('user-payment-status').value,
            membership_tier: document.getElementById('user-membership-tier').value,
            membership_expiry_date: document.getElementById('user-expiry-date').value || null
        };
        
        try {
            const response = await window.WOVCCAuth.authenticatedFetch(`/admin/users/${currentEditingUser.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                if (typeof showNotification === 'function') {
                    showNotification('User updated successfully', 'success');
                }
                closeUserModal();
                loadAdminUsers(currentPage);
                loadAdminStats(); // Refresh stats
            } else {
                if (typeof showNotification === 'function') {
                    showNotification(result.error || 'Failed to update user', 'error');
                }
            }
        } catch (error) {
            console.error('Failed to update user:', error);
            if (typeof showNotification === 'function') {
                showNotification('Failed to update user', 'error');
            }
        }
    }
    
    async function deleteUser(userId, userName) {
        if (!confirm(`Are you sure you want to delete ${userName}? This action cannot be undone.`)) {
            return;
        }
        
        try {
            const response = await window.WOVCCAuth.authenticatedFetch(`/admin/users/${userId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                if (typeof showNotification === 'function') {
                    showNotification('User deleted successfully', 'success');
                }
                loadAdminUsers(currentPage);
                loadAdminStats(); // Refresh stats
            } else {
                if (typeof showNotification === 'function') {
                    showNotification(result.error || 'Failed to delete user', 'error');
                }
            }
        } catch (error) {
            console.error('Failed to delete user:', error);
            if (typeof showNotification === 'function') {
                showNotification('Failed to delete user', 'error');
            }
        }
    }
    
    // Export functions to global scope
    window.AdminUsers = {
        loadUsers: loadAdminUsers,
        applyFilter,
        applySearch,
        sortBy,
        closeUserModal,
        handleUserSubmit
    };

    // Delegated, CSP-safe events for Users admin

    // Filter buttons
    document.addEventListener('click', function(e) {
        const filterBtn = e.target.closest('[data-admin-users-filter]');
        if (filterBtn) {
            e.preventDefault();
            const filter = filterBtn.getAttribute('data-admin-users-filter');
            if (filter) {
                applyFilter(filter);
            }
            return;
        }

        // Sort headers
        const sortHeader = e.target.closest('[data-admin-users-sort]');
        if (sortHeader) {
            e.preventDefault();
            const field = sortHeader.getAttribute('data-admin-users-sort');
            if (field) {
                sortBy(field);
            }
            return;
        }

        // Pagination buttons
        const pageBtn = e.target.closest('[data-admin-users-page]');
        if (pageBtn) {
            e.preventDefault();
            const page = parseInt(pageBtn.getAttribute('data-admin-users-page'), 10);
            if (!isNaN(page)) {
                loadAdminUsers(page);
            }
            return;
        }

        // User modal close buttons
        const closeUserBtn = e.target.closest('[data-admin-users-action="close-user-modal"]');
        if (closeUserBtn) {
            e.preventDefault();
            closeUserModal();
            return;
        }
    });

    // Search input: trigger search on Enter key without inline JS
    document.addEventListener('keydown', function(e) {
        const input = e.target;
        if (input && input.matches('[data-admin-users-search-input]') && e.key === 'Enter') {
            e.preventDefault();
            applySearch(input.value || '');
        }
    });

    // User edit form submit (no inline onsubmit)
    const userForm = document.getElementById('user-form');
    if (userForm) {
        userForm.addEventListener('submit', handleUserSubmit);
    }
})();

