// ===================================
// WOVCC Events Page Controller
// Handles events listing and detail pages
// ===================================

(function() {
  'use strict';

// Check if we're on the events listing page or detail page
const isListingPage = window.location.pathname === '/events';
const isDetailPage = window.location.pathname.startsWith('/events/');

// API Base URL
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5000/api'
  : 'https://api.wovcc.co.uk/api';

// ===================================
// EVENTS LISTING PAGE
// ===================================

if (isListingPage) {
  let allEvents = [];
  let currentFilter = 'upcoming';
  let currentCategory = 'all';
  let searchTerm = '';

  document.addEventListener('DOMContentLoaded', function() {
    initEventsPage();
  });

  async function initEventsPage() {
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
    
    // Time display
    const timeDisplay = event.time ? `
      <div class="event-card-meta-item">
        <svg fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
        </svg>
        <span>${event.time}</span>
      </div>
    ` : '';
    
    // Location display
    const locationDisplay = event.location ? `
      <div class="event-card-meta-item">
        <svg fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/>
        </svg>
        <span>${event.location}</span>
      </div>
    ` : '';
    
    return `
      <div class="event-card" onclick="window.location.href='/events/${event.id}'">
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
      </div>
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
        ${Array(6).fill(0).map(() => `
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
    document.getElementById('category-filter').addEventListener('change', function() {
      currentCategory = this.value;
      loadEvents();
    });
    
    // Search input (with debounce)
    let searchTimeout;
    document.getElementById('search-input').addEventListener('input', function() {
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

if (isDetailPage) {
  let currentEvent = null;
  let userInterested = false;

  document.addEventListener('DOMContentLoaded', function() {
    if (typeof EVENT_ID !== 'undefined') {
      loadEventDetail(EVENT_ID);
      setupDetailEventListeners();
    }
  });

  async function loadEventDetail(eventId) {
    try {
      // Show skeleton
      document.getElementById('event-skeleton').style.display = 'block';
      document.getElementById('event-content').style.display = 'none';
      document.getElementById('event-error').style.display = 'none';
      
      const response = await fetch(`${API_BASE}/events/${eventId}`);
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
  }

  function renderEventDetail(event) {
    // Hide skeleton, show content
    document.getElementById('event-skeleton').style.display = 'none';
    document.getElementById('event-content').style.display = 'block';
    
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
    
    // Render markdown for long description
    if (typeof marked !== 'undefined') {
      document.getElementById('event-long-description').innerHTML = marked.parse(event.long_description);
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
      mapIframe.src = `https://www.google.com/maps/embed/v1/place?key=&q=${encodedLocation}`;
      
      // Show map (Google Maps Embed API is free for basic usage without API key for some browsers)
      // For production, you should get a free API key from Google Cloud Console
      mapContainer.style.display = 'block';
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
  }

  function setupDetailEventListeners() {
    // Interest button
    document.getElementById('interest-button').addEventListener('click', handleInterestClick);
    
    // Modal close buttons
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal-cancel').addEventListener('click', closeModal);
    
    // Interest form
    document.getElementById('interest-form').addEventListener('submit', handleInterestSubmit);
    
    // Close modal on outside click
    document.getElementById('interest-modal').addEventListener('click', function(e) {
      if (e.target === this) {
        closeModal();
      }
    });
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
        const token = localStorage.getItem('wovcc_access_token');
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
    document.getElementById('event-skeleton').style.display = 'none';
    document.getElementById('event-content').style.display = 'none';
    document.getElementById('event-error').style.display = 'block';
  }
}

})(); // End IIFE
