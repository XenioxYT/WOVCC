(function () {
  'use strict';

  // Admin Sponsors Management Module
  window.AdminSponsors = window.AdminSponsors || {};

  let allSponsors = [];
  let currentEditingSponsor = null;
  let currentFilter = 'all';
  let currentSearch = '';

  // Load all sponsors
  async function loadSponsors() {
    try {
      showLoadingState();

      const params = new URLSearchParams({
        filter: currentFilter,
        search: currentSearch
      });

      const response = await window.WOVCCAuth.authenticatedFetch(`/sponsors/admin?${params}`);
      const data = await response.json();

      if (data.success) {
        allSponsors = data.sponsors || [];
        renderSponsorsTable(allSponsors);
      } else {
        showError('Failed to load sponsors: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error loading sponsors:', error);
      showError('Failed to load sponsors');
    }
  }

  // Show loading state
  function showLoadingState() {
    const container = document.getElementById('admin-sponsors-list');
    if (!container) return;

    container.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <div class="skeleton-spinner"></div>
        <p style="margin-top: 15px; color: var(--text-light);">Loading sponsors...</p>
      </div>
    `;
  }

  // Render sponsors table
  function renderSponsorsTable(sponsors) {
    const container = document.getElementById('admin-sponsors-list');
    if (!container) return;

    if (!sponsors || sponsors.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px; color: var(--text-light);">
          <svg style="width: 48px; height: 48px; margin: 0 auto 15px; opacity: 0.5;" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
          </svg>
          <p style="margin: 0; font-size: 1.1rem;">No sponsors found</p>
          <p style="margin: 8px 0 0 0; font-size: 0.9rem;">Add your first sponsor to get started</p>
        </div>
      `;
      return;
    }

    const escapeHtml = window.HTMLSanitizer ? window.HTMLSanitizer.escapeHtml : (str => String(str));

    const tableHTML = `
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="background: var(--secondary-bg); border-bottom: 2px solid var(--border-color);">
              <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark); width: 80px;">Logo</th>
              <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Name</th>
              <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Website</th>
              <th style="padding: 12px; text-align: center; font-weight: 600; color: var(--text-dark); width: 100px;">Order</th>
              <th style="padding: 12px; text-align: center; font-weight: 600; color: var(--text-dark); width: 100px;">Status</th>
              <th style="padding: 12px; text-align: center; font-weight: 600; color: var(--text-dark); width: 120px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${sponsors.map(sponsor => createSponsorRow(sponsor, escapeHtml)).join('')}
          </tbody>
        </table>
      </div>
    `;

    container.innerHTML = tableHTML;
    attachSponsorEventListeners();
  }

  // Create sponsor row
  function createSponsorRow(sponsor, escapeHtml) {
    const safeName = escapeHtml(sponsor.name);
    const safeWebsite = sponsor.website_url ? escapeHtml(sponsor.website_url) : '-';
    const safeId = parseInt(sponsor.id, 10);
    const statusClass = sponsor.is_active ? 'active' : 'inactive';
    const statusText = sponsor.is_active ? 'Active' : 'Inactive';

    return `
      <tr style="border-bottom: 1px solid var(--border-color);">
        <td style="padding: 12px;">
          <img 
            src="${escapeHtml(sponsor.logo_url)}" 
            alt="${safeName}" 
            style="height: 40px; width: auto; display: block; background: #f5f5f5; padding: 4px; border-radius: 4px;"
            loading="lazy">
        </td>
        <td style="padding: 12px; font-weight: 500; color: var(--text-dark);">${safeName}</td>
        <td style="padding: 12px; color: var(--text-light); font-size: 0.9rem;">
          ${sponsor.website_url ? `<a href="${escapeHtml(sponsor.website_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--primary-color); text-decoration: none;">${safeWebsite}</a>` : '-'}
        </td>
        <td style="padding: 12px; text-align: center; color: var(--text-dark); font-weight: 500;">${sponsor.display_order}</td>
        <td style="padding: 12px; text-align: center;">
          <span class="payment-status-badge ${statusClass}">${statusText}</span>
        </td>
        <td style="padding: 12px; text-align: center;">
          <div style="display: flex; gap: 8px; justify-content: center;">
            <button 
              data-sponsor-id="${safeId}"
              data-admin-sponsors-action="edit"
              class="btn-icon" 
              title="Edit sponsor">
              <svg fill="currentColor" viewBox="0 0 20 20">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
              </svg>
            </button>
            <button 
              data-sponsor-id="${safeId}"
              data-admin-sponsors-action="delete"
              class="btn-icon btn-icon-danger" 
              title="Delete sponsor">
              <svg fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>
        </td>
      </tr>
    `;
  }

  // Attach event listeners
  function attachSponsorEventListeners() {
    // Search input
    const searchInput = document.getElementById('sponsors-search');
    if (searchInput) {
      searchInput.addEventListener('input', debounce(function (e) {
        currentSearch = e.target.value.trim();
        loadSponsors();
      }, 300));
    }

    // Filter dropdown
    const filterSelect = document.getElementById('sponsors-filter');
    if (filterSelect) {
      filterSelect.addEventListener('change', function (e) {
        currentFilter = e.target.value;
        loadSponsors();
      });
    }
  }

  // Delegated event listeners for buttons
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-admin-sponsors-action]');
    if (!btn) return;

    const action = btn.getAttribute('data-admin-sponsors-action');

    if (action === 'open-create-modal') {
      e.preventDefault();
      openCreateModal();
    } else if (action === 'close-modal') {
      e.preventDefault();
      closeModal();
    } else if (action === 'edit') {
      e.preventDefault();
      const sponsorId = parseInt(btn.getAttribute('data-sponsor-id'), 10);
      const sponsor = allSponsors.find(s => s.id === sponsorId);
      if (sponsor) {
        openEditModal(sponsor);
      }
    } else if (action === 'delete') {
      e.preventDefault();
      const sponsorId = parseInt(btn.getAttribute('data-sponsor-id'), 10);
      const sponsor = allSponsors.find(s => s.id === sponsorId);
      if (sponsor) {
        deleteSponsor(sponsor);
      }
    }
  });

  // Open create modal
  function openCreateModal() {
    currentEditingSponsor = null;

    document.getElementById('sponsor-modal-title').textContent = 'Create Sponsor';
    document.getElementById('sponsor-submit-btn').textContent = 'Create Sponsor';
    document.getElementById('sponsor-form').reset();
    document.getElementById('sponsor-is-active').checked = true;

    // Hide logo preview
    document.getElementById('sponsor-logo-preview').style.display = 'none';

    // Mark logo as required for create
    document.getElementById('sponsor-logo').required = true;

    document.getElementById('sponsor-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  // Open edit modal
  function openEditModal(sponsor) {
    currentEditingSponsor = sponsor;

    document.getElementById('sponsor-modal-title').textContent = 'Edit Sponsor';
    document.getElementById('sponsor-submit-btn').textContent = 'Update Sponsor';

    // Populate form
    document.getElementById('sponsor-name').value = sponsor.name || '';
    document.getElementById('sponsor-website').value = sponsor.website_url || '';
    document.getElementById('sponsor-display-order').value = sponsor.display_order || 0;
    document.getElementById('sponsor-is-active').checked = sponsor.is_active;

    // Show current logo
    const previewImg = document.getElementById('sponsor-logo-preview-img');
    previewImg.src = sponsor.logo_url;
    document.getElementById('sponsor-logo-preview').style.display = 'block';

    // Logo not required for edit
    document.getElementById('sponsor-logo').required = false;

    document.getElementById('sponsor-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  // Close modal
  function closeModal() {
    document.getElementById('sponsor-modal').style.display = 'none';
    document.body.style.overflow = '';
    document.getElementById('sponsor-form').reset();
    currentEditingSponsor = null;
  }

  // Handle form submit
  // Handle form submit
  const sponsorForm = document.getElementById('sponsor-form');
  if (sponsorForm && !sponsorForm.dataset.listenerAttached) {
    sponsorForm.dataset.listenerAttached = 'true';

    sponsorForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      e.stopImmediatePropagation();

      const submitBtn = document.getElementById('sponsor-submit-btn');
      if (submitBtn.disabled) return;

      const formData = new FormData();
      formData.append('name', document.getElementById('sponsor-name').value.trim());
      formData.append('website_url', document.getElementById('sponsor-website').value.trim());
      formData.append('display_order', document.getElementById('sponsor-display-order').value);
      formData.append('is_active', document.getElementById('sponsor-is-active').checked ? 'true' : 'false');

      const logoInput = document.getElementById('sponsor-logo');
      if (logoInput.files.length > 0) {
        formData.append('logo', logoInput.files[0]);
      }

      const originalText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = 'Saving...';

      try {
        let url, method;
        if (currentEditingSponsor) {
          url = `/sponsors/admin/${currentEditingSponsor.id}`;
          method = 'PUT';
        } else {
          url = '/sponsors/admin';
          method = 'POST';
        }

        const response = await window.WOVCCAuth.authenticatedFetch(url, {
          method: method,
          body: formData
        });

        const data = await response.json();

        if (data.success) {
          showSuccess(currentEditingSponsor ? 'Sponsor updated successfully' : 'Sponsor created successfully');
          closeModal();
          loadSponsors();
        } else {
          showError('Failed to save sponsor: ' + (data.error || 'Unknown error'));
        }
      } catch (error) {
        console.error('Error saving sponsor:', error);
        showError('Failed to save sponsor');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    });
  }

  // Logo preview on file select
  document.getElementById('sponsor-logo').addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function (event) {
        const previewImg = document.getElementById('sponsor-logo-preview-img');
        previewImg.src = event.target.result;
        document.getElementById('sponsor-logo-preview').style.display = 'block';
      };
      reader.readAsDataURL(file);
    }
  });

  // Delete sponsor
  async function deleteSponsor(sponsor) {
    if (!confirm(`Are you sure you want to delete "${sponsor.name}"?\n\nThis will permanently remove the sponsor and their logo. This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await window.WOVCCAuth.authenticatedFetch(`/sponsors/admin/${sponsor.id}`, {
        method: 'DELETE'
      });

      const data = await response.json();

      if (data.success) {
        showSuccess('Sponsor deleted successfully');
        loadSponsors();
      } else {
        showError('Failed to delete sponsor: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error deleting sponsor:', error);
      showError('Failed to delete sponsor');
    }
  }

  // Helper functions
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  function showError(message) {
    // Use the global notification system from admin-page.js
    if (typeof showNotification === 'function') {
      showNotification(message, 'error');
    } else if (typeof window.showDomNotification === 'function') {
      window.showDomNotification(message, 'error');
    } else {
      console.error(message);
      alert('Error: ' + message);
    }
  }

  function showSuccess(message) {
    // Use the global notification system from admin-page.js
    if (typeof showNotification === 'function') {
      showNotification(message, 'success');
    } else if (typeof window.showDomNotification === 'function') {
      window.showDomNotification(message, 'success');
    } else {
      console.log(message);
      alert(message);
    }
  }

  // Expose loadSponsors for tab initialization
  window.AdminSponsors.loadSponsors = loadSponsors;

})();
