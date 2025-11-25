(function() {
  'use strict';

  // Admin Content Management Module
  window.AdminContent = window.AdminContent || {};

  let allSnippets = [];
  let currentEditingKey = null;

  // Load all content snippets
  async function loadContentSnippets() {
    try {
      showLoadingState();

      const response = await window.WOVCCAuth.authenticatedFetch('/admin/content');
      const data = await response.json();

      if (data.success) {
        allSnippets = data.snippets || [];
        renderContentList(allSnippets);
      } else {
        showError('Failed to load content snippets: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error loading content snippets:', error);
      showError('Failed to load content snippets');
    }
  }

  // Show loading state
  function showLoadingState() {
    const container = document.getElementById('admin-content-list');
    if (!container) return;

    container.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <div class="skeleton-spinner"></div>
        <p style="margin-top: 15px; color: var(--text-light);">Loading content...</p>
      </div>
    `;
  }

  // Render content list
  function renderContentList(snippets) {
    const container = document.getElementById('admin-content-list');
    if (!container) return;

    if (!snippets || snippets.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px; color: var(--text-light);">
          <svg style="width: 48px; height: 48px; margin: 0 auto 15px; opacity: 0.5;" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
          </svg>
          <p>No content snippets found. Initialize the database to create default snippets.</p>
        </div>
      `;
      return;
    }

    const html = `
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
          <thead>
            <tr style="background: var(--secondary-bg); border-bottom: 2px solid var(--border-color);">
              <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Key</th>
              <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Description</th>
              <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Preview</th>
              <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Last Updated</th>
              <th style="padding: 12px; text-align: center; font-weight: 600; color: var(--text-dark);">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${snippets.map(snippet => `
              <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: 12px;">
                  <code style="background: var(--secondary-bg); padding: 4px 8px; border-radius: 4px; font-size: 0.85rem;">${escapeHtml(snippet.key)}</code>
                </td>
                <td style="padding: 12px; color: var(--text-light);">${escapeHtml(snippet.description || 'No description')}</td>
                <td style="padding: 12px; color: var(--text-dark); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  ${escapeHtml(snippet.content.substring(0, 80))}${snippet.content.length > 80 ? '...' : ''}
                </td>
                <td style="padding: 12px; color: var(--text-light); white-space: nowrap;">
                  ${snippet.updated_at ? formatDate(snippet.updated_at) : 'Never'}
                </td>
                <td style="padding: 12px; text-align: center;">
                  <button 
                    class="btn-icon" 
                    title="Edit Content"
                    data-admin-content-action="edit-snippet"
                    data-snippet-key="${escapeHtml(snippet.key)}"
                  >
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
                    </svg>
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    container.innerHTML = html;

    // Attach event listeners
    attachContentEventListeners();
  }

  // Attach event listeners for content actions
  function attachContentEventListeners() {
    // Edit snippet buttons
    document.querySelectorAll('[data-admin-content-action="edit-snippet"]').forEach(btn => {
      btn.addEventListener('click', function() {
        const key = this.getAttribute('data-snippet-key');
        openEditModal(key);
      });
    });

    // Close modal buttons
    document.querySelectorAll('[data-admin-content-action="close-content-modal"]').forEach(btn => {
      btn.addEventListener('click', closeContentModal);
    });

    // Form submit
    const form = document.getElementById('content-form');
    if (form) {
      form.removeEventListener('submit', handleContentFormSubmit);
      form.addEventListener('submit', handleContentFormSubmit);
    }
  }

  // Open edit modal
  function openEditModal(key) {
    const snippet = allSnippets.find(s => s.key === key);
    if (!snippet) {
      showError('Content snippet not found');
      return;
    }

    currentEditingKey = key;

    const modal = document.getElementById('content-modal');
    const keyInput = document.getElementById('content-key');
    const descInput = document.getElementById('content-description');
    const contentInput = document.getElementById('content-text');

    if (!modal || !keyInput || !descInput || !contentInput) return;

    keyInput.value = snippet.key;
    descInput.value = snippet.description || '';
    contentInput.value = snippet.content;

    modal.style.display = 'flex';

    // Focus on content textarea
    setTimeout(() => {
      contentInput.focus();
      contentInput.setSelectionRange(contentInput.value.length, contentInput.value.length);
    }, 100);
  }

  // Close content modal
  function closeContentModal() {
    const modal = document.getElementById('content-modal');
    if (!modal) return;

    modal.style.display = 'none';
    currentEditingKey = null;

    // Reset form
    const form = document.getElementById('content-form');
    if (form) form.reset();
  }

  // Handle content form submit
  async function handleContentFormSubmit(e) {
    e.preventDefault();

    const key = document.getElementById('content-key').value;
    const content = document.getElementById('content-text').value.trim();

    if (!content) {
      showError('Content cannot be empty');
      return;
    }

    try {
      const submitBtn = document.getElementById('content-submit-btn');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Updating...';
      }

      const response = await window.WOVCCAuth.authenticatedFetch(`/admin/content/${encodeURIComponent(key)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });

      const data = await response.json();

      if (data.success) {
        showSuccess('Content updated successfully');
        closeContentModal();
        loadContentSnippets(); // Reload list
      } else {
        showError('Failed to update content: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error updating content:', error);
      showError('Failed to update content');
    } finally {
      const submitBtn = document.getElementById('content-submit-btn');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Update Content';
      }
    }
  }

  // Helper functions
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatDate(dateString) {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return dateString;
    }
  }

  function showError(message) {
    if (typeof window.showNotification === 'function') {
      window.showNotification(message, 'error');
    } else {
      console.error(message);
      // Use mobile-friendly modal as fallback
      if (window.WOVCCModal) {
        window.WOVCCModal.alert({ title: 'Error', message: message, type: 'danger' });
      }
    }
  }

  function showSuccess(message) {
    if (typeof window.showNotification === 'function') {
      window.showNotification(message, 'success');
    } else {
      console.log(message);
    }
  }

  // Export public API
  window.AdminContent.loadContentSnippets = loadContentSnippets;
  window.AdminContent.closeContentModal = closeContentModal;
})();
