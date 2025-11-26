/**
 * WOVCC Modal Utilities
 * Provides mobile-friendly modal dialogs to replace browser alerts, confirms, and prompts
 */

(function() {
  'use strict';

  // CSS styles for modals
  const modalStyles = `
    .wovcc-modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10001;
      padding: 20px;
      box-sizing: border-box;
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      animation: wovccModalFadeIn 0.2s ease-out;
      overflow-y: auto;
    }

    @keyframes wovccModalFadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes wovccModalSlideIn {
      from {
        transform: translateY(30px) scale(0.95);
        opacity: 0;
      }
      to {
        transform: translateY(0) scale(1);
        opacity: 1;
      }
    }

    .wovcc-modal-container {
      background: white;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      width: 100%;
      max-width: 420px;
      max-height: 90vh;
      overflow: hidden;
      animation: wovccModalSlideIn 0.3s ease-out;
      display: flex;
      flex-direction: column;
    }

    .wovcc-modal-header {
      padding: 20px 24px 16px;
      display: flex;
      align-items: flex-start;
      gap: 16px;
    }

    .wovcc-modal-icon {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .wovcc-modal-icon svg {
      width: 24px;
      height: 24px;
    }

    .wovcc-modal-icon.warning {
      background: #fef3c7;
      color: #d97706;
    }

    .wovcc-modal-icon.danger {
      background: #fee2e2;
      color: #dc2626;
    }

    .wovcc-modal-icon.info {
      background: #dbeafe;
      color: #2563eb;
    }

    .wovcc-modal-icon.success {
      background: #d1fae5;
      color: #059669;
    }

    .wovcc-modal-header-content {
      flex: 1;
      min-width: 0;
    }

    .wovcc-modal-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: #1a1a1a;
      margin: 0 0 4px 0;
      line-height: 1.4;
    }

    .wovcc-modal-message {
      font-size: 0.95rem;
      color: #6c757d;
      margin: 0;
      line-height: 1.5;
      word-wrap: break-word;
    }

    .wovcc-modal-body {
      padding: 0 24px 16px;
    }

    .wovcc-modal-input {
      width: 100%;
      padding: 12px 16px;
      border: 2px solid #e9ecef;
      border-radius: 8px;
      font-size: 1rem;
      font-family: inherit;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
      box-sizing: border-box;
    }

    .wovcc-modal-input:focus {
      outline: none;
      border-color: #1a5f5f;
      box-shadow: 0 0 0 3px rgba(26, 95, 95, 0.1);
    }

    .wovcc-modal-footer {
      padding: 16px 24px 20px;
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      border-top: 1px solid #f1f3f4;
      background: #fafafa;
    }

    .wovcc-modal-btn {
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
      min-height: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 2px solid transparent;
    }

    .wovcc-modal-btn:focus {
      outline: 2px solid #1a5f5f;
      outline-offset: 2px;
    }

    .wovcc-modal-btn-cancel {
      background: white;
      border-color: #e9ecef;
      color: #6c757d;
    }

    .wovcc-modal-btn-cancel:hover {
      background: #f8f9fa;
      border-color: #dee2e6;
    }

    .wovcc-modal-btn-confirm {
      background: #1a5f5f;
      color: white;
    }

    .wovcc-modal-btn-confirm:hover {
      background: #144a4a;
      transform: translateY(-1px);
    }

    .wovcc-modal-btn-confirm.danger {
      background: #dc2626;
    }

    .wovcc-modal-btn-confirm.danger:hover {
      background: #b91c1c;
    }

    .wovcc-modal-btn-confirm.warning {
      background: #d97706;
    }

    .wovcc-modal-btn-confirm.warning:hover {
      background: #b45309;
    }

    /* Mobile optimizations */
    @media screen and (max-width: 575px) {
      .wovcc-modal-overlay {
        padding: 15px;
        align-items: flex-start;
        padding-top: 60px;
      }

      .wovcc-modal-container {
        max-width: 100%;
        border-radius: 12px;
      }

      .wovcc-modal-header {
        padding: 16px 20px 12px;
      }

      .wovcc-modal-icon {
        width: 40px;
        height: 40px;
      }

      .wovcc-modal-icon svg {
        width: 20px;
        height: 20px;
      }

      .wovcc-modal-title {
        font-size: 1rem;
      }

      .wovcc-modal-message {
        font-size: 0.9rem;
      }

      .wovcc-modal-body {
        padding: 0 20px 12px;
      }

      .wovcc-modal-footer {
        padding: 12px 20px 16px;
        flex-direction: column-reverse;
      }

      .wovcc-modal-btn {
        width: 100%;
        padding: 12px 20px;
      }

      .wovcc-modal-input {
        font-size: 16px; /* Prevents zoom on iOS */
      }
    }
  `;

  // Inject styles once
  if (!document.getElementById('wovcc-modal-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'wovcc-modal-styles';
    styleEl.textContent = modalStyles;
    document.head.appendChild(styleEl);
  }

  // Icon SVGs
  const icons = {
    warning: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
    danger: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
    info: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>',
    success: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
    question: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/></svg>'
  };

  /**
   * Create and show a modal dialog
   * @param {Object} options - Modal configuration
   * @returns {Promise} Resolves with user action
   */
  function createModal(options) {
    return new Promise((resolve) => {
      const {
        title = 'Confirm',
        message = '',
        type = 'info', // info, warning, danger, success
        confirmText = 'OK',
        cancelText = 'Cancel',
        showCancel = true,
        input = null, // { type: 'text', placeholder: '', value: '' }
        dangerous = false
      } = options;

      // Create overlay
      const overlay = document.createElement('div');
      overlay.className = 'wovcc-modal-overlay';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-labelledby', 'wovcc-modal-title');

      // Determine icon type
      const iconType = dangerous ? 'danger' : type;
      const iconHtml = icons[iconType] || icons.info;

      // Build modal HTML
      let bodyHtml = '';
      if (input) {
        bodyHtml = `
          <div class="wovcc-modal-body">
            <input 
              type="${input.type || 'text'}" 
              class="wovcc-modal-input" 
              id="wovcc-modal-input"
              placeholder="${input.placeholder || ''}"
              value="${input.value || ''}"
              autocomplete="off"
            >
          </div>
        `;
      }

      overlay.innerHTML = `
        <div class="wovcc-modal-container">
          <div class="wovcc-modal-header">
            <div class="wovcc-modal-icon ${iconType}">
              ${iconHtml}
            </div>
            <div class="wovcc-modal-header-content">
              <h3 class="wovcc-modal-title" id="wovcc-modal-title">${escapeHtml(title)}</h3>
              <p class="wovcc-modal-message">${escapeHtml(message)}</p>
            </div>
          </div>
          ${bodyHtml}
          <div class="wovcc-modal-footer">
            ${showCancel ? `<button type="button" class="wovcc-modal-btn wovcc-modal-btn-cancel">${escapeHtml(cancelText)}</button>` : ''}
            <button type="button" class="wovcc-modal-btn wovcc-modal-btn-confirm ${dangerous ? 'danger' : ''}">${escapeHtml(confirmText)}</button>
          </div>
        </div>
      `;

      // Add to DOM
      document.body.appendChild(overlay);
      document.body.style.overflow = 'hidden';

      // Get elements
      const container = overlay.querySelector('.wovcc-modal-container');
      const confirmBtn = overlay.querySelector('.wovcc-modal-btn-confirm');
      const cancelBtn = overlay.querySelector('.wovcc-modal-btn-cancel');
      const inputEl = overlay.querySelector('#wovcc-modal-input');

      // Focus management
      if (inputEl) {
        inputEl.focus();
        inputEl.select();
      } else {
        confirmBtn.focus();
      }

      // Cleanup function
      function cleanup() {
        overlay.style.opacity = '0';
        overlay.style.transition = 'opacity 0.2s ease';
        setTimeout(() => {
          if (overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
          }
          document.body.style.overflow = '';
        }, 200);
      }

      // Handle confirm
      function handleConfirm() {
        cleanup();
        if (input && inputEl) {
          resolve({ confirmed: true, value: inputEl.value });
        } else {
          resolve({ confirmed: true });
        }
      }

      // Handle cancel
      function handleCancel() {
        cleanup();
        resolve({ confirmed: false });
      }

      // Event listeners
      confirmBtn.addEventListener('click', handleConfirm);
      
      if (cancelBtn) {
        cancelBtn.addEventListener('click', handleCancel);
      }

      // Close on overlay click
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          handleCancel();
        }
      });

      // Close on Escape key
      function handleKeydown(e) {
        if (e.key === 'Escape') {
          handleCancel();
          document.removeEventListener('keydown', handleKeydown);
        } else if (e.key === 'Enter' && input && inputEl) {
          e.preventDefault();
          handleConfirm();
        }
      }
      document.addEventListener('keydown', handleKeydown);

      // Trap focus within modal
      container.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
          const focusable = container.querySelectorAll('button, input');
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      });
    });
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Show a confirmation dialog (replaces window.confirm)
   * @param {string|Object} messageOrOptions - Message string or full options object
   * @returns {Promise<boolean>} Resolves to true if confirmed, false if cancelled
   */
  async function confirm(messageOrOptions) {
    const options = typeof messageOrOptions === 'string' 
      ? { message: messageOrOptions }
      : messageOrOptions;
    
    const result = await createModal({
      title: options.title || 'Confirm',
      message: options.message || '',
      type: options.type || 'warning',
      confirmText: options.confirmText || 'Confirm',
      cancelText: options.cancelText || 'Cancel',
      showCancel: true,
      dangerous: options.dangerous || false
    });
    
    return result.confirmed;
  }

  /**
   * Show an alert dialog (replaces window.alert)
   * @param {string|Object} messageOrOptions - Message string or full options object
   * @returns {Promise<void>}
   */
  async function alert(messageOrOptions) {
    const options = typeof messageOrOptions === 'string' 
      ? { message: messageOrOptions }
      : messageOrOptions;
    
    await createModal({
      title: options.title || 'Notice',
      message: options.message || '',
      type: options.type || 'info',
      confirmText: options.confirmText || 'OK',
      showCancel: false
    });
  }

  /**
   * Show a prompt dialog (replaces window.prompt)
   * @param {string|Object} messageOrOptions - Message string or full options object
   * @returns {Promise<string|null>} Resolves to input value or null if cancelled
   */
  async function prompt(messageOrOptions) {
    const options = typeof messageOrOptions === 'string' 
      ? { message: messageOrOptions }
      : messageOrOptions;
    
    const result = await createModal({
      title: options.title || 'Input Required',
      message: options.message || '',
      type: options.type || 'info',
      confirmText: options.confirmText || 'OK',
      cancelText: options.cancelText || 'Cancel',
      showCancel: true,
      input: {
        type: options.inputType || 'text',
        placeholder: options.placeholder || '',
        value: options.defaultValue || ''
      }
    });
    
    return result.confirmed ? result.value : null;
  }

  /**
   * Show a delete confirmation dialog with dangerous styling
   * @param {string} itemName - Name of item being deleted
   * @param {string} additionalMessage - Optional additional warning message
   * @returns {Promise<boolean>}
   */
  async function confirmDelete(itemName, additionalMessage = '') {
    let message = `Are you sure you want to delete "${itemName}"?`;
    if (additionalMessage) {
      message += '\n\n' + additionalMessage;
    }
    
    return confirm({
      title: 'Delete ' + itemName + '?',
      message: message,
      type: 'danger',
      confirmText: 'Delete',
      cancelText: 'Cancel',
      dangerous: true
    });
  }

  /**
   * Show a clear/reset confirmation dialog
   * @param {string} actionDescription - Description of what will be cleared
   * @returns {Promise<boolean>}
   */
  async function confirmClear(actionDescription) {
    return confirm({
      title: 'Clear Configuration?',
      message: actionDescription,
      type: 'warning',
      confirmText: 'Clear',
      cancelText: 'Cancel',
      dangerous: false
    });
  }

  // Export to global scope
  window.WOVCCModal = {
    confirm,
    alert,
    prompt,
    confirmDelete,
    confirmClear,
    createModal
  };

})();
