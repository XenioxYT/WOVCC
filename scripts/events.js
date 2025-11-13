// ===================================
// WOVCC Events Page Controller
// Handles events listing and detail pages
// ===================================

(function() {
  'use strict';

// API Base URL
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5000/api'
  : 'https://wovcc.xeniox.uk/api';

// Check if we're on the events listing page or detail page
function isListingPage() {
  return window.location.pathname === '/events';
}

function isDetailPage() {
  return window.location.pathname.startsWith('/events/');
}

// ===================================
// EVENTS LISTING PAGE
// ===================================

// Listing page variables and functions
let allEvents = [];
let currentFilter = 'upcoming';
let currentCategory = 'all';
let searchTerm = '';
let listenersInitialized = false;
let listingPageInitialized = false;

// Unified initialization for the listing page.
document.addEventListener('pageTransitionComplete', function(e) {
  if (e.detail.path === '/events') {
    // Initialize the page if it hasn't been for this view
    if (!listingPageInitialized) {
      showSkeleton(); // Show placeholder immediately on transition
      initEventsPage();
      listingPageInitialized = true;
    }
  } else {
    // When navigating away, reset the state for the next visit.
    listingPageInitialized = false;
    listenersInitialized = false;
  }
});

// Fallback for the very first page load.
document.addEventListener('DOMContentLoaded', () => {
    if(isListingPage() && !listingPageInitialized) {
        showSkeleton(); // Show placeholder immediately on hard load
        initEventsPage();
        listingPageInitialized = true;
    }
});

async function initEventsPage() {
  if (!isListingPage()) return;
  
  // Load categories
  await loadCategories();
  
  // Load events
  await loadEvents();
  
  // Setup event listeners
  setupEventListeners();
}

async function loadCategories() {
    try {
      const response = await fetch(`${API_BASE}/events/categories`);
      const data = await response.json();
      
      if (data.success && data.categories) {
        const categoryFilter = document.getElementById('category-filter');
        if (!categoryFilter) {
          console.error('Category filter element not found');
          return;
        }
        
        // Clear existing options (except the first "All Categories" option)
        while (categoryFilter.options.length > 1) {
          categoryFilter.remove(1);
        }
        
        // Add new categories
        data.categories.forEach(cat => {
          const option = document.createElement('option');
          option.value = cat;
          option.textContent = cat;
          categoryFilter.appendChild(option);
        });
      }
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  }

  async function loadEvents() {
    try {
      // Show skeleton loader
      showSkeleton();
      
      const params = new URLSearchParams({
        filter: currentFilter,
        category: currentCategory,
        search: searchTerm
      });
      
      const response = await fetch(`${API_BASE}/events?${params}`);
      const data = await response.json();
      
      if (data.success) {
        allEvents = data.events;
        renderEvents(allEvents);
      } else {
        showNoEvents();
      }
    } catch (error) {
      console.error('Failed to load events:', error);
      showNoEvents();
    }
  }

  function renderEvents(events) {
    const container = document.getElementById('events-container');
    const noEventsMessage = document.getElementById('no-events-message');
    const skeleton = document.getElementById('events-skeleton');
    
    skeleton.style.display = 'none';
    
    if (!events || events.length === 0) {
      container.style.display = 'none';
      noEventsMessage.style.display = 'block';
      return;
    }
    
    container.style.display = 'grid';
    noEventsMessage.style.display = 'none';
    
    container.innerHTML = events.map(event => createEventCard(event)).join('');
  }

  function createEventCard(event) {
    const hasImage = event.image_url && event.image_url.trim() !== '';
    const imageUrl = hasImage ? event.image_url : '/assets/logo.webp';
    const categoryBadge = event.category ? `<div class="event-card-category">${event.category}</div>` : '';
    
    // Format date
    const eventDate = new Date(event.date);
    const dateDisplay = eventDate.toLocaleDateString('en-GB', { 
      day: 'numeric', 
      month: 'short', 
      year: 'numeric' 
    });
    
    // Time display - check for truthy value and non-empty string
    const timeDisplay = (event.time && event.time.trim() !== '') ? `
      <div class="event-card-meta-item">
        <svg fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
        </svg>
        <span>${event.time}</span>
      </div>
    ` : '';
    
    // Location display - check for truthy value and non-empty string
    const locationDisplay = (event.location && event.location.trim() !== '') ? `
      <div class="event-card-meta-item">
        <svg fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/>
        </svg>
        <span>${event.location}</span>
      </div>
    ` : '';
    
    return `
      <a href="/events/${event.id}" class="event-card" style="text-decoration: none; color: inherit; display: block;">
        <div class="event-card-image-container ${hasImage ? 'has-image' : ''}" style="${hasImage ? `--card-image: url('${imageUrl}');` : ''}">
          <img src="${imageUrl}" alt="${event.title}" class="event-card-image" onerror="this.src='/assets/logo.webp'">
        </div>
        <div class="event-card-body">
          ${categoryBadge}
          <h3 class="event-card-title">${event.title}</h3>
          <p class="event-card-description">${event.short_description}</p>
          <div class="event-card-meta">
            <div class="event-card-meta-item">
              <svg fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
              </svg>
              <span>${dateDisplay}</span>
            </div>
            ${timeDisplay}
            ${locationDisplay}
            ${event.interested_count > 0 ? `
              <div class="event-card-interested">
                <svg fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/>
                </svg>
                <span>${event.interested_count} interested</span>
              </div>
            ` : ''}
          </div>
        </div>
      </a>
    `;
  }

  function showSkeleton() {
    const container = document.getElementById('events-container');
    const skeleton = document.getElementById('events-skeleton');
    const noEventsMessage = document.getElementById('no-events-message');
    
    container.style.display = 'none';
    noEventsMessage.style.display = 'none';
    skeleton.style.display = 'block';
    
    skeleton.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 25px;">
        ${Array(12).fill(0).map(() => `
          <div class="skeleton-event-card">
            <div class="skeleton-image"></div>
            <div class="skeleton-content">
              <div class="skeleton-line short" style="width: 30%; margin-bottom: 10px;"></div>
              <div class="skeleton-line title" style="margin-bottom: 12px;"></div>
              <div class="skeleton-line long" style="margin-bottom: 8px;"></div>
              <div class="skeleton-line medium" style="margin-bottom: 20px;"></div>
              <div class="skeleton-line short" style="width: 40%;"></div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function showNoEvents() {
    const container = document.getElementById('events-container');
    const skeleton = document.getElementById('events-skeleton');
    const noEventsMessage = document.getElementById('no-events-message');
    
    container.style.display = 'none';
    skeleton.style.display = 'none';
    noEventsMessage.style.display = 'block';
  }

  function setupEventListeners() {
    // Only set up listeners once to avoid duplicates
    if (listenersInitialized) return;
    listenersInitialized = true;
    
    // Filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', function() {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        currentFilter = this.dataset.filter;
        loadEvents();
      });
    });
    
    // Category filter
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
      categoryFilter.addEventListener('change', function() {
        currentCategory = this.value;
        loadEvents();
      });
    }
    
    // Search input (with debounce)
    let searchTimeout;
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
          searchTerm = this.value.trim();
          loadEvents();
        }, 300);
      });
    }
  }

// ===================================
// EVENT DETAIL PAGE
// ===================================

// Event detail page variables (always define these, check page type when needed)
let currentEvent = null;
let userInterested = false;
let detailListenersInitialized = false;

// Function to extract event ID from URL
function getEventIdFromUrl() {
  const pathParts = window.location.pathname.split('/');
  return pathParts[pathParts.length - 1];
}

// Initialize detail page
function initDetailPage() {
  if (!isDetailPage()) return;
  
  const eventId = getEventIdFromUrl();
  if (eventId) {
    loadEventDetail(eventId);
    // Note: setupDetailEventListeners() is called inside loadEventDetail() after rendering
  }
}

// Initialize on DOMContentLoaded if we're on detail page
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    if (isDetailPage()) {
      initDetailPage();
    }
  });
} else {
  if (isDetailPage()) {
    initDetailPage();
  }
}

// Re-initialize on page transitions
document.addEventListener('pageTransitionComplete', function(e) {
  if (e.detail.path.startsWith('/events/') && e.detail.path !== '/events') {
    // Reset state when navigating to a detail page
    detailListenersInitialized = false;
    currentEvent = null;
    userInterested = false;
    
    // Add a small delay to ensure DOM is ready
    setTimeout(() => {
      initDetailPage();
    }, 100);
  } else if (!e.detail.path.startsWith('/events/')) {
    // Reset state when navigating away from detail pages
    detailListenersInitialized = false;
    currentEvent = null;
    userInterested = false;
  }
});

async function loadEventDetail(eventId) {
  try {
    // Show skeleton with fade-in
    const skeleton = document.getElementById('event-skeleton');
    const content = document.getElementById('event-content');
    const error = document.getElementById('event-error');
    
    // Hide content and error first
    if (content) {
      content.classList.remove('loaded');
      content.style.display = 'none';
    }
    if (error) {
      error.classList.remove('active');
      error.style.display = 'none';
    }
    
    // Show skeleton with proper transition
    if (skeleton) {
      skeleton.style.display = 'block';
      // Force reflow to ensure display change is applied before adding the active class
      void skeleton.offsetHeight;
      // Use requestAnimationFrame to ensure the transition triggers
      requestAnimationFrame(() => {
        skeleton.classList.add('active');
      });
    }
    
      const headers = {};
    // Check both sessionStorage and localStorage for backward compatibility during transition
    const token = sessionStorage.getItem('wovcc_access_token') || localStorage.getItem('wovcc_access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(`${API_BASE}/events/${eventId}`, { headers });
    const data = await response.json();
    
    if (data.success && data.event) {
      currentEvent = data.event;
      userInterested = data.event.user_interested || false;
      renderEventDetail(data.event);
      setupDetailEventListeners();
    } else {
      showError();
    }
  } catch (error) {
    console.error('Failed to load event:', error);
    showError();
  }
}  function renderEventDetail(event) {
    // Fade out skeleton first
    const skeleton = document.getElementById('event-skeleton');
    const content = document.getElementById('event-content');
    
    // Remove active class to fade out skeleton
    if (skeleton && skeleton.classList.contains('active')) {
      skeleton.classList.remove('active');
      
      // Wait for skeleton fade-out before showing content
      setTimeout(() => {
        skeleton.style.display = 'none';
        
        // Show content with fade-in
        if (content) {
          content.style.display = 'block';
          void content.offsetHeight;
          requestAnimationFrame(() => {
            content.classList.add('loaded');
          });
        }
      }, 300); // Match the CSS transition duration
    } else {
      // Fallback if skeleton doesn't exist or wasn't shown
      if (skeleton) {
        skeleton.style.display = 'none';
      }
      if (content) {
        content.style.display = 'block';
        void content.offsetHeight;
        requestAnimationFrame(() => {
          content.classList.add('loaded');
        });
      }
    }
    
    // Set title
    document.getElementById('event-title').textContent = event.title;
    document.title = `${event.title} - WOVCC`;
    
    // Set category
    if (event.category) {
      document.getElementById('event-category').textContent = event.category;
      document.getElementById('event-category').style.display = 'inline-block';
    }
    
    // Set descriptions
    document.getElementById('event-short-description').textContent = event.short_description;
    
    // Render markdown for long description with sanitization
    if (typeof marked !== 'undefined') {
      const rawHtml = marked.parse(event.long_description);
      // Security: Sanitize the HTML output from marked to prevent XSS
      if (window.HTMLSanitizer && window.HTMLSanitizer.sanitizeHtml) {
        document.getElementById('event-long-description').innerHTML = window.HTMLSanitizer.sanitizeHtml(rawHtml);
      } else {
        // Fallback: use textContent if sanitizer is not available
        document.getElementById('event-long-description').textContent = event.long_description;
      }
    } else {
      document.getElementById('event-long-description').textContent = event.long_description;
    }
    
    // Set banner image
    if (event.image_url) {
      const bannerContainer = document.getElementById('event-banner-container');
      const bannerImage = document.getElementById('event-banner');
      
      bannerImage.src = event.image_url;
      bannerImage.alt = event.title;
      bannerContainer.style.display = 'flex';
      
      // Set the blurred background image using CSS custom property
      bannerContainer.classList.add('has-image');
      bannerContainer.style.setProperty('--banner-image', `url("${event.image_url}")`);
    } else {
      document.getElementById('event-banner-container').style.display = 'none';
    }
    
    // Set date
    const eventDate = new Date(event.date);
    document.getElementById('event-date-display').textContent = eventDate.toLocaleDateString('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
    
    // Set time
    if (event.time) {
      document.getElementById('event-time').textContent = event.time;
      document.getElementById('event-time-container').style.display = 'block';
    }
    
    // Set location
    if (event.location) {
      document.getElementById('event-location').textContent = event.location;
      document.getElementById('event-location-container').style.display = 'block';
      
      // Try to show Google Maps embed
      const mapContainer = document.getElementById('event-map-container');
      const mapIframe = document.getElementById('event-map');
      const encodedLocation = encodeURIComponent(event.location);
      
      // Get API key from data attribute
      const apiKey = mapIframe.getAttribute('data-maps-api-key') || '';
      
      if (apiKey) {
        mapIframe.src = `https://www.google.com/maps/embed/v1/place?key=${apiKey}&q=${encodedLocation}`;
        mapContainer.style.display = 'block';
      } else {
        console.warn('Google Maps API key not found. Map will not be displayed.');
        // Hide map container if no API key
        mapContainer.style.display = 'none';
      }
    }
    
    // Set interested count
    document.getElementById('interested-count').textContent = event.interested_count || 0;
    
    // Update interest button
    updateInterestButton();
    
    // Show recurring info
    if (event.is_recurring && event.recurrence_pattern) {
      document.getElementById('recurring-info').style.display = 'block';
      const patternText = event.recurrence_pattern === 'daily' ? 'Daily' : 
                         event.recurrence_pattern === 'weekly' ? 'Weekly' : 
                         event.recurrence_pattern === 'monthly' ? 'Monthly' : event.recurrence_pattern;
      
      let endDateText = '';
      if (event.recurrence_end_date) {
        const endDate = new Date(event.recurrence_end_date);
        endDateText = ` until ${endDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`;
      }
      
      document.getElementById('recurring-pattern').textContent = `${patternText}${endDateText}`;
    }
  }

  function updateInterestButton() {
    const button = document.getElementById('interest-button');
    const text = document.getElementById('interest-text');
    const icon = document.getElementById('interest-icon');
    if (!button || !text || !icon) {
      return;
    }
    
    if (userInterested) {
      text.textContent = "I'm Interested ✓";
      button.classList.add('btn-primary');
      button.classList.remove('btn-outline');
      icon.style.fill = 'currentColor';
    } else {
      text.textContent = "I'm Interested";
      button.classList.add('btn-outline');
      button.classList.remove('btn-primary');
    }

    button.dataset.initialInterested = userInterested ? 'true' : 'false';
    button.setAttribute('aria-pressed', userInterested ? 'true' : 'false');
  }

  function setupDetailEventListeners() {
    // Only set up listeners once to avoid duplicates
    if (detailListenersInitialized) return;
    detailListenersInitialized = true;
    
    // Interest button
    const interestButton = document.getElementById('interest-button');
    if (interestButton) {
      interestButton.addEventListener('click', handleInterestClick);
    }
    
    // Modal close buttons
    const modalClose = document.getElementById('modal-close');
    const modalCancel = document.getElementById('modal-cancel');
    if (modalClose) {
      modalClose.addEventListener('click', closeModal);
    }
    if (modalCancel) {
      modalCancel.addEventListener('click', closeModal);
    }
    
    // Interest form
    const interestForm = document.getElementById('interest-form');
    if (interestForm) {
      interestForm.addEventListener('submit', handleInterestSubmit);
    }
    
    // Close modal on outside click
    const interestModal = document.getElementById('interest-modal');
    if (interestModal) {
      interestModal.addEventListener('click', function(e) {
        if (e.target === this) {
          closeModal();
        }
      });
    }
  }

  async function handleInterestClick() {
    // Check if user is logged in
    const isLoggedIn = window.WOVCCAuth && window.WOVCCAuth.isLoggedIn();
    
    if (isLoggedIn) {
      // Toggle interest directly
      await toggleInterest();
    } else {
      // Show modal for non-members
      document.getElementById('interest-modal').style.display = 'flex';
    }
  }

  async function toggleInterest(email = null, name = null) {
    try {
      const body = email ? JSON.stringify({ email, name }) : null;
      
      const headers = {
        'Content-Type': 'application/json'
      };
      
      // Add auth token if logged in
      if (window.WOVCCAuth && window.WOVCCAuth.isLoggedIn()) {
        // Check both sessionStorage and localStorage for backward compatibility
        const token = sessionStorage.getItem('wovcc_access_token') || localStorage.getItem('wovcc_access_token');
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      }
      
      const response = await fetch(`${API_BASE}/events/${currentEvent.id}/interest`, {
        method: 'POST',
        headers,
        body
      });
      
      const data = await response.json();
      
      if (data.success) {
        userInterested = data.action === 'added';
        currentEvent.interested_count = data.interested_count;
        
        // Update UI
        document.getElementById('interested-count').textContent = data.interested_count;
        updateInterestButton();
        
        if (typeof showNotification === 'function') {
          showNotification(
            data.action === 'added' ? 'Thanks for showing your interest!' : 'Interest removed',
            'success'
          );
        }
      } else {
        if (typeof showNotification === 'function') {
          showNotification(data.error || 'Failed to update interest', 'error');
        }
      }
    } catch (error) {
      console.error('Failed to toggle interest:', error);
      if (typeof showNotification === 'function') {
        showNotification('Failed to update interest', 'error');
      }
    }
  }

  async function handleInterestSubmit(e) {
    e.preventDefault();
    
    const name = document.getElementById('interest-name').value.trim();
    const email = document.getElementById('interest-email').value.trim();
    
    if (!email) {
      if (typeof showNotification === 'function') {
        showNotification('Please enter your email', 'warning');
      }
      return;
    }
    
    await toggleInterest(email, name);
    closeModal();
  }

  function closeModal() {
    document.getElementById('interest-modal').style.display = 'none';
    document.getElementById('interest-form').reset();
  }

  function showError() {
    const skeleton = document.getElementById('event-skeleton');
    const content = document.getElementById('event-content');
    const error = document.getElementById('event-error');
    
    // Hide content first
    if (content) {
      content.classList.remove('loaded');
      content.style.display = 'none';
    }
    
    // Fade out skeleton
    if (skeleton) {
      skeleton.classList.remove('active');
      
      setTimeout(() => {
        skeleton.style.display = 'none';
        
        // Show error with fade-in
        if (error) {
          error.style.display = 'block';
          void error.offsetHeight;
          requestAnimationFrame(() => {
            error.classList.add('active');
          });
        }
      }, 300);
    } else {
      // Fallback if skeleton doesn't exist
      if (error) {
        error.style.display = 'block';
        void error.offsetHeight;
        requestAnimationFrame(() => {
          error.classList.add('active');
        });
      }
    }
  }

})(); // End IIFE
