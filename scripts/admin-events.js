// ===================================
// WOVCC Admin Events Management
// Handles event creation, editing, and deletion
// ===================================

(function() {
  'use strict';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5000/api'
  : 'https://api.wovcc.co.uk/api';

let allEvents = [];
let currentEditingEvent = null;
let selectedImage = null;
let imagePreviewUrl = null;

// Initialize when admin page loads
if (window.location.pathname === '/admin') {
  document.addEventListener('DOMContentLoaded', function() {
    // Check if events tab exists (will be added to admin.html)
    const eventsTab = document.getElementById('events-tab');
    if (eventsTab) {
      eventsTab.addEventListener('click', function() {
        loadAdminEvents();
      });
    }
    
    // If events tab is active on load, load events
    if (document.getElementById('events-tab-content')?.style.display !== 'none') {
      loadAdminEvents();
    }
  });
}

async function loadAdminEvents() {
  console.log('loadAdminEvents called');
  try {
    showEventsLoading();
    
    console.log('Fetching events from /events?show_all=true&filter=all');
    const response = await window.WOVCCAuth.authenticatedFetch(`/events?show_all=true&filter=all`);
    const data = await response.json();
    
    console.log('Events data received:', data);
    
    if (data.success) {
      allEvents = data.events;
      console.log('Rendering', allEvents.length, 'events');
      renderAdminEventsList(allEvents);
    } else {
      console.error('API returned success: false', data);
      showEventsError('Failed to load events');
    }
  } catch (error) {
    console.error('Failed to load events:', error);
    showEventsError(error.message);
  }
}

function renderAdminEventsList(events) {
  console.log('renderAdminEventsList called with', events?.length, 'events');
  const container = document.getElementById('admin-events-list');
  console.log('Container element:', container);
  if (!container) {
    console.error('admin-events-list container not found!');
    return;
  }
  
  if (!events || events.length === 0) {
    console.log('No events to display');
    container.innerHTML = `
      <div style="text-align: center; padding: 40px; color: var(--text-light);">
        <p>No events yet. Create your first event!</p>
      </div>
    `;
    return;
  }
  
  // Sort by date (newest first)
  events.sort((a, b) => new Date(b.date) - new Date(a.date));
  
  container.innerHTML = `
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr style="background: var(--secondary-bg); border-bottom: 2px solid var(--border-color);">
            <th style="padding: 12px; text-align: left; font-weight: 600;">Title</th>
            <th style="padding: 12px; text-align: left; font-weight: 600;">Date</th>
            <th style="padding: 12px; text-align: left; font-weight: 600;">Category</th>
            <th style="padding: 12px; text-align: center; font-weight: 600;">Interested</th>
            <th style="padding: 12px; text-align: center; font-weight: 600;">Status</th>
            <th style="padding: 12px; text-align: center; font-weight: 600;">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${events.map(event => createEventRow(event)).join('')}
        </tbody>
      </table>
    </div>
  `;
  
  // Attach event listeners
  events.forEach(event => {
    document.getElementById(`edit-event-${event.id}`)?.addEventListener('click', () => openEditEventModal(event));
    document.getElementById(`delete-event-${event.id}`)?.addEventListener('click', () => deleteEvent(event.id));
    document.getElementById(`view-interested-${event.id}`)?.addEventListener('click', () => viewInterestedUsers(event.id));
  });
}

function createEventRow(event) {
  const eventDate = new Date(event.date);
  const dateDisplay = eventDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  const statusBadge = event.is_published 
    ? '<span style="background: #d4edda; color: #155724; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">Published</span>'
    : '<span style="background: #fff3cd; color: #856404; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">Draft</span>';
  
  return `
    <tr style="border-bottom: 1px solid var(--border-color);">
      <td style="padding: 12px;">
        <div style="font-weight: 600; color: var(--text-dark); margin-bottom: 4px;">${event.title}</div>
        <div style="font-size: 0.85rem; color: var(--text-light);">${event.short_description.substring(0, 60)}${event.short_description.length > 60 ? '...' : ''}</div>
      </td>
      <td style="padding: 12px; white-space: nowrap;">${dateDisplay}</td>
      <td style="padding: 12px;">${event.category || '-'}</td>
      <td style="padding: 12px; text-align: center;">
        <button id="view-interested-${event.id}" style="background: none; border: none; color: var(--primary-color); cursor: pointer; font-weight: 600; text-decoration: underline;">
          ${event.interested_count || 0}
        </button>
      </td>
      <td style="padding: 12px; text-align: center;">${statusBadge}</td>
      <td style="padding: 12px; text-align: center;">
        <div style="display: flex; gap: 10px; justify-content: center;">
          <button id="edit-event-${event.id}" class="btn-icon" title="Edit">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
            </svg>
          </button>
          <button id="delete-event-${event.id}" class="btn-icon btn-icon-danger" title="Delete">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
      </td>
    </tr>
  `;
}

function showEventsLoading() {
  const container = document.getElementById('admin-events-list');
  if (!container) return;
  
  container.innerHTML = `
    <div style="text-align: center; padding: 40px;">
      <div class="skeleton-spinner"></div>
      <p style="margin-top: 15px; color: var(--text-light);">Loading events...</p>
    </div>
  `;
}

function showEventsError(message) {
  const container = document.getElementById('admin-events-list');
  if (!container) return;
  
  container.innerHTML = `
    <div style="text-align: center; padding: 40px; color: var(--accent-color);">
      <p>${message}</p>
    </div>
  `;
}

function openCreateEventModal() {
  currentEditingEvent = null;
  selectedImage = null;
  imagePreviewUrl = null;
  
  const modal = document.getElementById('event-modal');
  if (!modal) return;
  
  // Reset form
  document.getElementById('event-form').reset();
  document.getElementById('event-modal-title').textContent = 'Create New Event';
  document.getElementById('event-submit-btn').textContent = 'Create Event';
  document.getElementById('image-preview-container').style.display = 'none';
  document.getElementById('recurring-options').style.display = 'none';
  document.getElementById('markdown-preview').innerHTML = '';
  
  modal.style.display = 'flex';
}

function openEditEventModal(event) {
  currentEditingEvent = event;
  selectedImage = null;
  imagePreviewUrl = event.image_url;
  
  const modal = document.getElementById('event-modal');
  if (!modal) return;
  
  // Populate form
  document.getElementById('event-title').value = event.title;
  document.getElementById('event-short-description').value = event.short_description;
  document.getElementById('event-long-description').value = event.long_description;
  document.getElementById('event-date').value = new Date(event.date).toISOString().slice(0, 16);
  document.getElementById('event-time').value = event.time || '';
  document.getElementById('event-location').value = event.location || '';
  document.getElementById('event-category').value = event.category || '';
  document.getElementById('event-is-recurring').checked = event.is_recurring || false;
  document.getElementById('event-recurrence-pattern').value = event.recurrence_pattern || 'weekly';
  document.getElementById('event-recurrence-end-date').value = event.recurrence_end_date ? new Date(event.recurrence_end_date).toISOString().slice(0, 10) : '';
  document.getElementById('event-is-published').checked = event.is_published || false;
  
  // Show image preview if exists
  if (imagePreviewUrl) {
    document.getElementById('image-preview').src = imagePreviewUrl;
    document.getElementById('image-preview-container').style.display = 'block';
  }
  
  // Show/hide recurring options
  document.getElementById('recurring-options').style.display = event.is_recurring ? 'block' : 'none';
  
  // Update markdown preview
  updateMarkdownPreview();
  
  document.getElementById('event-modal-title').textContent = 'Edit Event';
  document.getElementById('event-submit-btn').textContent = 'Update Event';
  
  modal.style.display = 'flex';
}

function closeEventModal() {
  const modal = document.getElementById('event-modal');
  if (modal) {
    modal.style.display = 'none';
  }
  currentEditingEvent = null;
  selectedImage = null;
  imagePreviewUrl = null;
}

async function handleEventSubmit(e) {
  e.preventDefault();
  
  const formData = new FormData();
  formData.append('title', document.getElementById('event-title').value);
  formData.append('short_description', document.getElementById('event-short-description').value);
  formData.append('long_description', document.getElementById('event-long-description').value);
  formData.append('date', document.getElementById('event-date').value);
  formData.append('time', document.getElementById('event-time').value);
  formData.append('location', document.getElementById('event-location').value);
  formData.append('category', document.getElementById('event-category').value);
  formData.append('is_recurring', document.getElementById('event-is-recurring').checked);
  formData.append('recurrence_pattern', document.getElementById('event-recurrence-pattern').value);
  formData.append('recurrence_end_date', document.getElementById('event-recurrence-end-date').value);
  formData.append('is_published', document.getElementById('event-is-published').checked);
  
  // Add image if selected
  if (selectedImage) {
    formData.append('image', selectedImage);
  }
  
  try {
    const url = currentEditingEvent 
      ? `${API_BASE}/events/${currentEditingEvent.id}`
      : `${API_BASE}/events`;
    
    const method = currentEditingEvent ? 'PUT' : 'POST';
    
    const token = localStorage.getItem('wovcc_access_token');
    const response = await fetch(url, {
      method,
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    const data = await response.json();
    
    if (data.success) {
      if (typeof showNotification === 'function') {
        showNotification(data.message, 'success');
      }
      closeEventModal();
      loadAdminEvents();
    } else {
      if (typeof showNotification === 'function') {
        showNotification(data.error || 'Failed to save event', 'error');
      }
    }
  } catch (error) {
    console.error('Failed to save event:', error);
    if (typeof showNotification === 'function') {
      showNotification('Failed to save event', 'error');
    }
  }
}

async function deleteEvent(eventId) {
  if (!confirm('Are you sure you want to delete this event? This action cannot be undone.')) {
    return;
  }
  
  try {
    const response = await window.WOVCCAuth.authenticatedFetch(`/events/${eventId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    
    if (data.success) {
      if (typeof showNotification === 'function') {
        showNotification('Event deleted successfully', 'success');
      }
      loadAdminEvents();
    } else {
      if (typeof showNotification === 'function') {
        showNotification(data.error || 'Failed to delete event', 'error');
      }
    }
  } catch (error) {
    console.error('Failed to delete event:', error);
    if (typeof showNotification === 'function') {
      showNotification('Failed to delete event', 'error');
    }
  }
}

async function viewInterestedUsers(eventId) {
  try {
    const response = await window.WOVCCAuth.authenticatedFetch(`/events/${eventId}/interested-users`);
    const data = await response.json();
    
    if (data.success) {
      showInterestedUsersModal(data.users, data.count);
    } else {
      if (typeof showNotification === 'function') {
        showNotification('Failed to load interested users', 'error');
      }
    }
  } catch (error) {
    console.error('Failed to load interested users:', error);
    if (typeof showNotification === 'function') {
      showNotification('Failed to load interested users', 'error');
    }
  }
}

function showInterestedUsersModal(users, count) {
  const modal = document.getElementById('interested-users-modal');
  if (!modal) return;
  
  const container = document.getElementById('interested-users-list');
  
  if (!users || users.length === 0) {
    container.innerHTML = `
      <p style="text-align: center; padding: 20px; color: var(--text-light);">
        No one has shown interest yet.
      </p>
    `;
  } else {
    container.innerHTML = `
      <div style="margin-bottom: 15px; color: var(--text-light);">
        <strong>${count}</strong> ${count === 1 ? 'person has' : 'people have'} shown interest in this event.
      </div>
      <div style="max-height: 400px; overflow-y: auto;">
        ${users.map(user => `
          <div style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 10px;">
            <svg style="width: 20px; height: 20px; color: var(--primary-color);" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
            </svg>
            <div style="flex: 1;">
              <div style="font-weight: 600; color: var(--text-dark);">
                ${user.name}
                ${user.is_member ? '<span style="font-size: 0.75rem; background: var(--primary-color); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">Member</span>' : ''}
              </div>
              <div style="font-size: 0.9rem; color: var(--text-light);">${user.email}</div>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-light);">
              ${new Date(user.created_at).toLocaleDateString('en-GB')}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }
  
  modal.style.display = 'flex';
}

function closeInterestedUsersModal() {
  const modal = document.getElementById('interested-users-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function handleImageSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  // Validate file type
  const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
  if (!validTypes.includes(file.type)) {
    if (typeof showNotification === 'function') {
      showNotification('Invalid file type. Please select a PNG, JPG, or WebP image.', 'error');
    }
    return;
  }
  
  // Validate file size (5MB)
  if (file.size > 5 * 1024 * 1024) {
    if (typeof showNotification === 'function') {
      showNotification('File too large. Maximum size is 5MB.', 'error');
    }
    return;
  }
  
  selectedImage = file;
  
  // Show preview
  const reader = new FileReader();
  reader.onload = function(e) {
    imagePreviewUrl = e.target.result;
    document.getElementById('image-preview').src = imagePreviewUrl;
    document.getElementById('image-preview-container').style.display = 'block';
  };
  reader.readAsDataURL(file);
}

function removeImage() {
  selectedImage = null;
  imagePreviewUrl = null;
  document.getElementById('event-image').value = '';
  document.getElementById('image-preview-container').style.display = 'none';
}

function toggleRecurringOptions() {
  const isRecurring = document.getElementById('event-is-recurring').checked;
  document.getElementById('recurring-options').style.display = isRecurring ? 'block' : 'none';
}

function updateMarkdownPreview() {
  const longDescription = document.getElementById('event-long-description').value;
  const preview = document.getElementById('markdown-preview');
  
  if (typeof marked !== 'undefined') {
    preview.innerHTML = marked.parse(longDescription);
  } else {
    preview.textContent = longDescription;
  }
}

// Export functions for use in admin.html
window.AdminEvents = {
  loadAdminEvents,
  openCreateEventModal,
  closeEventModal,
  handleEventSubmit,
  closeInterestedUsersModal,
  handleImageSelect,
  removeImage,
  toggleRecurringOptions,
  updateMarkdownPreview
};

})(); // End IIFE
