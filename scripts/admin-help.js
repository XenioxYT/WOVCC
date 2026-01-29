(function () {
  'use strict';

  // Admin Help Chat Module
  window.AdminHelp = window.AdminHelp || {};

  let conversationHistory = [];
  let isProcessing = false;

  // Initialize chat
  function initChat() {
    const form = document.getElementById('help-chat-form');
    const input = document.getElementById('help-chat-input');

    // Check if form exists and hasn't had listeners attached yet
    // Use a data attribute to track if this specific DOM element has listeners
    if (!form) return;
    if (form.dataset.chatInitialized === 'true') return;
    form.dataset.chatInitialized = 'true';

    form.addEventListener('submit', handleChatSubmit);

    if (input) {
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          form.dispatchEvent(new Event('submit'));
        }
      });
    }
  }

  // Handle chat form submission
  async function handleChatSubmit(e) {
    e.preventDefault();

    if (isProcessing) return;

    const input = document.getElementById('help-chat-input');
    const userMessage = input.value.trim();

    if (!userMessage) return;

    // Clear input
    input.value = '';

    // Add user message to chat
    addMessage(userMessage, 'user');

    // Show loading indicator
    showLoading();

    // Update status
    updateStatus('Getting response...');

    isProcessing = true;

    try {
      // Send message to API
      const response = await window.WOVCCAuth.authenticatedFetch('/admin/help/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          history: conversationHistory
        })
      });

      const data = await response.json();

      // Remove loading indicator
      removeLoading();

      if (data.success) {
        // Add assistant response to chat
        addMessage(data.message, 'assistant');

        // Update conversation history
        conversationHistory.push(
          { role: 'user', content: userMessage },
          { role: 'assistant', content: data.message }
        );

        // Keep only last 10 messages to manage token usage
        if (conversationHistory.length > 20) {
          conversationHistory = conversationHistory.slice(-20);
        }

        updateStatus('');
      } else {
        removeLoading();
        addMessage('Sorry, I encountered an error: ' + (data.error || 'Unknown error'), 'error');
        updateStatus('Error - please try again');
      }
    } catch (error) {
      console.error('Chat error:', error);
      removeLoading();
      addMessage('Sorry, I couldn\'t connect to the AI assistant. Please check your internet connection and try again.', 'error');
      updateStatus('Connection error');
    } finally {
      isProcessing = false;
    }
  }

  // Add message to chat
  function addMessage(content, type) {
    const messagesContainer = document.getElementById('help-chat-messages');
    if (!messagesContainer) return;

    const messageDiv = document.createElement('div');

    if (type === 'user') {
      messageDiv.className = 'chat-message user-message';
      messageDiv.innerHTML = `
        <div class="message-avatar">
          <svg style="width: 20px; height: 20px;" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="message-content">
          <p>${escapeHtml(content)}</p>
        </div>
      `;
    } else if (type === 'error') {
      messageDiv.className = 'chat-message assistant-message';
      messageDiv.innerHTML = `
        <div class="message-avatar" style="background: var(--accent-color);">
          <svg style="width: 20px; height: 20px;" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="message-content" style="background: #fee; border-color: #fcc;">
          <p>${escapeHtml(content)}</p>
        </div>
      `;
    } else {
      // Assistant message
      messageDiv.className = 'chat-message assistant-message';
      messageDiv.innerHTML = `
        <div class="message-avatar">
          <svg style="width: 20px; height: 20px;" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"/>
            <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"/>
          </svg>
        </div>
        <div class="message-content">
          ${formatMessage(content)}
        </div>
      `;
    }

    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Format message content using markdown
  function formatMessage(content) {
    // Use marked.js to parse markdown
    if (typeof marked !== 'undefined') {
      // Configure marked options for better security and formatting
      marked.setOptions({
        breaks: true, // Convert \n to <br>
        gfm: true, // GitHub Flavored Markdown
        headerIds: false, // Don't add IDs to headers
        mangle: false // Don't escape email addresses
      });

      return marked.parse(content);
    }

    // Fallback if marked is not available
    return escapeHtml(content).replace(/\n/g, '<br>');
  }

  // Show loading indicator
  function showLoading() {
    const messagesContainer = document.getElementById('help-chat-messages');
    if (!messagesContainer) return;

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-message assistant-message';
    loadingDiv.id = 'chat-loading-indicator';
    loadingDiv.innerHTML = `
      <div class="message-avatar">
        <svg style="width: 20px; height: 20px;" fill="currentColor" viewBox="0 0 20 20">
          <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"/>
          <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"/>
        </svg>
      </div>
      <div class="message-content">
        <div class="chat-loading">
          <div class="chat-loading-dot"></div>
          <div class="chat-loading-dot"></div>
          <div class="chat-loading-dot"></div>
        </div>
      </div>
    `;

    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Remove loading indicator
  function removeLoading() {
    const loadingIndicator = document.getElementById('chat-loading-indicator');
    if (loadingIndicator) {
      loadingIndicator.remove();
    }
  }

  // Update status message
  function updateStatus(message) {
    const statusElement = document.getElementById('help-chat-status');
    if (statusElement) {
      statusElement.textContent = message;
    }
  }

  // Escape HTML to prevent XSS
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Clear chat history
  function clearChat() {
    const messagesContainer = document.getElementById('help-chat-messages');
    if (!messagesContainer) return;

    // Keep only the welcome message
    const welcomeMessage = messagesContainer.querySelector('.assistant-message');
    messagesContainer.innerHTML = '';
    if (welcomeMessage) {
      messagesContainer.appendChild(welcomeMessage.cloneNode(true));
    }

    conversationHistory = [];
    updateStatus('');
  }

  // Export public API
  window.AdminHelp.initChat = initChat;
  window.AdminHelp.clearChat = clearChat;
})();
