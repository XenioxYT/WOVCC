/**
 * WOVCC Admin Dashboard
 * Displays statistics and metrics for the admin panel
 */

(function() {
  'use strict';

  let statsData = null;

  /**
   * Initialize the dashboard
   */
  function initDashboard() {
    loadStats();
  }

  /**
   * Load statistics from the API
   */
  async function loadStats() {
    try {
      if (!window.WOVCCAuth || !window.WOVCCAuth.authenticatedFetch) {
        console.error('WOVCCAuth not available');
        return;
      }

      const response = await window.WOVCCAuth.authenticatedFetch('/admin/stats');
      
      if (!response.ok) {
        throw new Error('Failed to load statistics');
      }

      const data = await response.json();
      
      if (data.success) {
        statsData = data.stats;
        renderStats();
      } else {
        console.error('Error loading stats:', data.error);
      }
    } catch (error) {
      console.error('Error loading dashboard stats:', error);
    }
  }

  /**
   * Render all statistics to the dashboard
   */
  function renderStats() {
    if (!statsData) return;

    // Member statistics
    document.getElementById('stat-total-members').textContent = statsData.total_members || 0;
    document.getElementById('stat-active-members').textContent = `${statsData.active_members || 0} active`;

    // Event statistics
    document.getElementById('stat-upcoming-events').textContent = statsData.upcoming_events || 0;
    document.getElementById('stat-total-events').textContent = `${statsData.published_events || 0} published`;

    // Newsletter subscribers
    document.getElementById('stat-newsletter').textContent = statsData.newsletter_subscribers || 0;

    // Expiring soon
    document.getElementById('stat-expiring-soon').textContent = statsData.expiring_soon || 0;

    // Payment status breakdown
    renderPaymentStatusBreakdown();

    // Recent activity
    renderRecentActivity();
  }

  /**
   * Render payment status breakdown
   */
  function renderPaymentStatusBreakdown() {
    const container = document.getElementById('payment-status-chart');
    if (!container) return;

    const breakdown = statsData.payment_status_breakdown || {};
    container.innerHTML = '';

    const preferredOrder = ['active', 'pending', 'expired', 'cancelled', 'unknown'];
    const orderedStatuses = [
      ...preferredOrder
        .filter(status => breakdown[status] !== undefined)
        .map(status => [status, breakdown[status]]),
      ...Object.entries(breakdown).filter(([status]) => !preferredOrder.includes(status))
    ];

    const totalCount = orderedStatuses.reduce((sum, [, count]) => sum + (Number(count) || 0), 0);

    if (orderedStatuses.length === 0 || totalCount === 0) {
      container.innerHTML = '<div style="color: var(--text-light);">No payment data available</div>';
      return;
    }

    orderedStatuses.forEach(([status, count]) => {
      const label = status ? status.replace(/_/g, ' ') : 'Unknown';
      const displayLabel = label.charAt(0).toUpperCase() + label.slice(1);
      const item = document.createElement('div');
      item.className = 'payment-status-item';
      item.innerHTML = `
        <span class="payment-status-badge ${status}">${displayLabel}</span>
        <span style="font-weight: 600; font-size: 1.2rem;">${count}</span>
      `;
      container.appendChild(item);
    });
  }

  /**
   * Render recent activity (signups)
   */
  function renderRecentActivity() {
    const container = document.getElementById('recent-activity');
    if (!container) return;

    const signups = statsData.recent_signups || [];
    container.innerHTML = '';

    if (signups.length === 0) {
      container.innerHTML = '<div style="color: var(--text-light); padding: 12px;">No recent signups</div>';
      return;
    }

    signups.forEach(user => {
      const item = document.createElement('div');
      item.className = 'activity-item';
      
      // Get initials for avatar
      const initials = user.name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .substring(0, 2);

      // Format date
      const date = new Date(user.created_at);
      const dateStr = date.toLocaleDateString('en-GB', { 
        day: 'numeric', 
        month: 'short',
        year: 'numeric'
      });

      item.innerHTML = `
        <div class="activity-avatar">${initials}</div>
        <div class="activity-details">
          <div class="activity-name">${escapeHtml(user.name)}</div>
          <div class="activity-date">Joined ${dateStr} • ${user.membership_tier}</div>
        </div>
      `;
      
      container.appendChild(item);
    });
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  /**
   * Refresh dashboard data
   */
  function refreshDashboard() {
    loadStats();
  }

  // Export functions for use by admin-page.js
  window.AdminDashboard = {
    init: initDashboard,
    refresh: refreshDashboard
  };
})();
