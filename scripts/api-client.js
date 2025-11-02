// ===================================
// WOVCC API Client
// Connects to Python backend API
// 
// Uses the /api/data endpoint with source=file
// to fetch pre-scraped data from scraped_data.json
// Data is cached locally for 5 minutes
// ===================================

// API Configuration
const API_CONFIG = {
  // Change this to your VPS URL after deployment
  baseURL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : 'https://api.wovcc.co.uk/api', // Replace with your actual API URL
  
  // Alternative: Use relative path if API is on same domain
  // baseURL: '/api',
  
  timeout: 10000 // 10 seconds
};

class WOVCCApi {
  constructor(config) {
    this.baseURL = config.baseURL;
    this.timeout = config.timeout;
    this.cachedData = null;
    this.cacheTimestamp = null;
    this.cacheMaxAge = 5 * 60 * 1000; // 5 minutes in milliseconds
    this.lastUpdated = null; // Store last updated timestamp from API
  }
  
  /**
   * Format relative time (e.g., "2 hours ago", "just now")
   * @param {string} isoString - ISO date string
   * @returns {string} Relative time string
   */
  formatRelativeTime(isoString) {
    if (!isoString) return 'Unknown';
    
    const now = new Date();
    const then = new Date(isoString);
    const diffMs = now - then;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
    if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
    if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
    
    // For older dates, show formatted date
    return then.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }
  
  /**
   * Get formatted last updated timestamp
   * @returns {object} { relative: string, full: string }
   */
  getLastUpdated() {
    if (!this.lastUpdated) return null;
    return {
      relative: this.formatRelativeTime(this.lastUpdated),
      full: new Date(this.lastUpdated).toLocaleString('en-GB', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    };
  }
  
  /**
   * Generic fetch wrapper with error handling
   */
  async _fetch(endpoint, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      
      console.error(`API Error (${endpoint}):`, error);
      throw error;
    }
  }
  
  /**
   * Fetch all data from the combined endpoint (uses scraped_data.json)
   * Caches the data locally for 5 minutes
   */
  async _fetchAllData() {
    // Check if cache is still valid
    const now = Date.now();
    if (this.cachedData && this.cacheTimestamp && (now - this.cacheTimestamp < this.cacheMaxAge)) {
      console.log('Using cached data');
      return this.cachedData;
    }
    
    try {
      console.log('Fetching fresh data from API...');
      const data = await this._fetch('/data?source=file');
      
      if (data.success) {
        this.cachedData = data;
        this.cacheTimestamp = now;
        this.lastUpdated = data.last_updated || null;
        console.log(`Data fetched successfully (last updated: ${data.last_updated})`);
        return data;
      } else {
        throw new Error('API returned unsuccessful response');
      }
    } catch (error) {
      console.error('Failed to fetch all data:', error);
      
      // If we have old cached data, use it as fallback
      if (this.cachedData) {
        console.warn('Using stale cached data as fallback');
        return this.cachedData;
      }
      
      throw error;
    }
  }
  
  /**
   * Health check
   */
  async healthCheck() {
    try {
      const data = await this._fetch('/health');
      return data;
    } catch (error) {
      console.error('Health check failed:', error);
      return { status: 'error', message: error.message };
    }
  }
  
  /**
   * Get all teams
   */
  async getTeams() {
    try {
      const data = await this._fetchAllData();
      return data.teams || [];
    } catch (error) {
      console.error('Failed to fetch teams:', error);
      return [];
    }
  }
  
  /**
   * Get fixtures
   * @param {string} teamId - Team ID or 'all' for all teams
   */
  async getFixtures(teamId = 'all') {
    try {
      const data = await this._fetchAllData();
      let fixtures = data.fixtures || [];
      
      // Filter by team if specified
      if (teamId && teamId !== 'all') {
        fixtures = fixtures.filter(f => f.team_id === teamId || f.team_id === String(teamId));
      }
      
      // Sort by date - most recent first (soonest upcoming first)
      fixtures.sort((a, b) => {
        const dateA = new Date(a.date_iso || a.date_str);
        const dateB = new Date(b.date_iso || b.date_str);
        return dateA - dateB; // Ascending order (soonest first)
      });
      
      return fixtures;
    } catch (error) {
      console.error('Failed to fetch fixtures:', error);
      return [];
    }
  }
  
  /**
   * Get results
   * @param {string} teamId - Team ID or 'all' for all teams
   * @param {number} limit - Number of results to return
   */
  async getResults(teamId = 'all', limit = 10) {
    try {
      const data = await this._fetchAllData();
      let results = data.results || [];
      
      // Filter by team if specified
      if (teamId && teamId !== 'all') {
        results = results.filter(r => r.team_id === teamId || r.team_id === String(teamId));
      }
      
      // Sort by date - most recent first (latest results first)
      results.sort((a, b) => {
        const dateA = new Date(a.date_iso || a.date_str);
        const dateB = new Date(b.date_iso || b.date_str);
        return dateB - dateA; // Descending order (most recent first)
      });
      
      // Apply limit
      if (limit && limit > 0) {
        results = results.slice(0, limit);
      }
      
      return results;
    } catch (error) {
      console.error('Failed to fetch results:', error);
      return [];
    }
  }
  
  /**
   * Check if there are matches today
   */
  async checkMatchStatus() {
    try {
      const data = await this._fetchAllData();
      const fixtures = data.fixtures || [];
      
      // Get today's date in ISO format (YYYY-MM-DD)
      const today = new Date().toISOString().split('T')[0];
      
      // Check if any fixture is scheduled for today
      const hasMatchesToday = fixtures.some(f => f.date_iso === today);
      
      return hasMatchesToday;
    } catch (error) {
      console.error('Failed to check match status:', error);
      return false;
    }
  }
  
  /**
   * Clear the local cache and force a fresh fetch on next request
   */
  clearCache() {
    this.cachedData = null;
    this.cacheTimestamp = null;
    this.lastUpdated = null;
    console.log('Local cache cleared');
  }
  
  /**
   * Render last updated timestamp
   * @param {HTMLElement} container - Container element to render into
   */
  renderLastUpdated(container) {
    if (!container) return;
    
    const lastUpdated = this.getLastUpdated();
    if (!lastUpdated) {
      container.innerHTML = '';
      return;
    }
    
    container.innerHTML = `
      <div class="last-updated-display" style="text-align: center; margin-top: 15px; padding: 10px 0; color: var(--text-light); font-size: 0.85rem;">
        <span style="color: var(--text-light);">Last updated:</span>
        <span class="last-updated-time" style="color: var(--primary-color); font-weight: 500; margin-left: 5px; cursor: help;" title="${lastUpdated.full}">
          ${lastUpdated.relative}
        </span>
      </div>
    `;
  }
  
  /**
   * Force refresh the data from the API
   */
  async refreshData() {
    this.clearCache();
    return await this._fetchAllData();
  }
  
  /**
   * Render skeleton loader for fixtures
   * @param {HTMLElement} container - Container element
   * @param {Number} count - Number of skeleton cards to show
   */
  renderFixturesSkeleton(container, count = 2) {
    if (!container) return;
    
    let html = '';
    for (let i = 0; i < count; i++) {
      html += `
        <div class="skeleton-card">
          <div class="skeleton-loader skeleton-line short" style="margin-bottom: 12px;"></div>
          <div class="skeleton-loader skeleton-line medium" style="margin-bottom: 8px;"></div>
          <div class="skeleton-loader skeleton-line long" style="margin-bottom: 8px;"></div>
          <div style="display: flex; gap: 15px; margin-top: 12px;">
            <div class="skeleton-loader skeleton-line short" style="width: 100px; height: 14px;"></div>
            <div class="skeleton-loader skeleton-line short" style="width: 120px; height: 14px;"></div>
          </div>
        </div>
      `;
    }
    container.innerHTML = html;
  }
  
  /**
   * Render skeleton loader for results
   * @param {HTMLElement} container - Container element
   * @param {Number} count - Number of skeleton cards to show
   */
  renderResultsSkeleton(container, count = 2) {
    if (!container) return;
    
    let html = '';
    for (let i = 0; i < count; i++) {
      html += `
        <div class="skeleton-card">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div class="skeleton-loader skeleton-line short" style="width: 120px; height: 16px;"></div>
            <div class="skeleton-loader skeleton-line short" style="width: 60px; height: 24px; border-radius: 12px;"></div>
          </div>
          <div class="skeleton-loader skeleton-line medium" style="margin-bottom: 8px;"></div>
          <div class="skeleton-loader skeleton-line long" style="margin-bottom: 8px;"></div>
          <div class="skeleton-loader skeleton-line medium" style="width: 70%; margin-top: 8px;"></div>
        </div>
      `;
    }
    container.innerHTML = html;
  }
  
  /**
   * Render loading spinner
   * @param {HTMLElement} container - Container element
   * @param {string} message - Optional loading message
   */
  renderLoadingSpinner(container, message = 'Loading...') {
    if (!container) return;
    
    container.innerHTML = `
      <div class="loading-spinner-container">
        <div class="skeleton-spinner"></div>
        <span>${message}</span>
      </div>
    `;
  }
  
  /**
   * Render fixtures to a container element
   * @param {Array} fixtures - Fixtures data
   * @param {HTMLElement} container - Container element
   * @param {Number} limit - Optional limit for number of fixtures to display (null = show all)
   */
  renderFixtures(fixtures, container, limit = null) {
    if (!container) return;
    
    if (!fixtures || fixtures.length === 0) {
      container.innerHTML = `
        <p style="text-align: center; color: var(--text-light); padding: 40px;">
          No upcoming fixtures found.
        </p>
      `;
      return;
    }
    
    // Apply limit if specified
    const displayFixtures = limit ? fixtures.slice(0, limit) : fixtures;
    let html = '';
    
    displayFixtures.forEach((fixture, index) => {
      const timeText = fixture.time ? `${fixture.time}` : '';
      const locationText = fixture.location ? `${fixture.location}` : '';
      const matchUrl = fixture.match_url || '#';
      
      html += `
        <a href="${matchUrl}" target="_blank" class="fixture-card-link fixture-item" style="text-decoration: none; color: inherit; display: block;">
          <div class="fixture-card">
            <div style="display: flex; justify-content: space-between; align-items: start; gap: 20px;">
              <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--primary-color); margin-bottom: 8px; font-size: 0.95rem;">
                  ${fixture.team_name_scraping || 'Team'}
                </div>
                <div style="color: var(--text-dark); margin-bottom: 10px; font-size: 1.05rem; font-weight: 500;">
                  <div style="margin-bottom: 4px;"><span style="font-size: 0.85rem; color: var(--text-light); font-weight: 400;">Home:</span> ${fixture.home_team}</div>
                  <div><span style="font-size: 0.85rem; color: var(--text-light); font-weight: 400;">Away:</span> ${fixture.away_team}</div>
                </div>
                <div style="display: flex; gap: 15px; flex-wrap: wrap; font-size: 0.85rem; color: var(--text-light);">
                  ${timeText ? `<div><svg style="width: 14px; height: 14px; display: inline-block; margin-right: 4px; vertical-align: middle;" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path></svg>${timeText}</div>` : ''}
                  ${locationText ? `<div><svg style="width: 14px; height: 14px; display: inline-block; margin-right: 4px; vertical-align: middle;" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"></path></svg>${locationText}</div>` : ''}
                </div>
              </div>
              <div style="text-align: right; font-size: 0.9rem; color: var(--text-light); white-space: nowrap; flex-shrink: 0;">
                <div style="font-weight: 600; color: var(--primary-color);">
                  ${fixture.date_str || fixture.date_iso || ''}
                </div>
              </div>
            </div>
          </div>
        </a>
      `;
    });
    
    container.innerHTML = html;
  }
  
  /**
   * Render results to a container element
   * @param {Array} results - Results data
   * @param {HTMLElement} container - Container element
   * @param {Number} limit - Optional limit for number of results to display (null = show all)
   */
  renderResults(results, container, limit = null) {
    if (!container) return;
    
    if (!results || results.length === 0) {
      container.innerHTML = `
        <p style="text-align: center; color: var(--text-light); padding: 40px;">
          No recent results found.
        </p>
      `;
      return;
    }
    
    // Apply limit if specified
    const displayResults = limit ? results.slice(0, limit) : results;
    let html = '';
    
    displayResults.forEach((result, index) => {
      const resultClass = result.is_win ? 'win' : result.is_loss ? 'loss' : 'draw';
      const matchUrl = result.match_url || '#';
      const resultLabel = result.is_win ? 'Won' : result.is_loss ? 'Lost' : 'Draw';
      
      html += `
        <a href="${matchUrl}" target="_blank" class="result-card-link result-item" style="text-decoration: none; color: inherit; display: block;">
          <div class="result-card ${resultClass}">
            <div style="display: flex; justify-content: space-between; align-items: start; gap: 20px;">
              <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                  <span style="font-weight: 600; color: var(--primary-color); font-size: 0.95rem;">
                    ${result.team_name_scraping || 'Team'}
                  </span>
                  <span style="font-size: 0.8rem; font-weight: 600; padding: 3px 10px; border-radius: 12px; ${result.is_win ? 'background: #d4edda; color: #155724;' : result.is_loss ? 'background: #f8d7da; color: #721c24;' : 'background: #fff3cd; color: #856404;'}">
                    ${resultLabel}
                  </span>
                </div>
                <div style="color: var(--text-dark); margin-bottom: 8px; font-size: 1.05rem; font-weight: 500;">
                  <div style="margin-bottom: 4px;"><span style="font-size: 0.85rem; color: var(--text-light); font-weight: 400;">Home:</span> ${result.home_team} ${result.home_score ? `<strong>${result.home_score}</strong>` : ''}</div>
                  <div><span style="font-size: 0.85rem; color: var(--text-light); font-weight: 400;">Away:</span> ${result.away_team} ${result.away_score ? `<strong>${result.away_score}</strong>` : ''}</div>
                </div>
                ${result.summary ? `<div style="font-size: 0.88rem; color: var(--text-light); line-height: 1.4; margin-top: 4px;">${result.summary}</div>` : ''}
              </div>
              <div style="text-align: right; font-size: 0.9rem; color: var(--text-light); white-space: nowrap; flex-shrink: 0;">
                <div style="font-weight: 600; color: var(--primary-color);">
                  ${result.date_str || result.date_iso || ''}
                </div>
              </div>
            </div>
          </div>
        </a>
      `;
    });
    
    container.innerHTML = html;
  }
}

// Initialize API client
const wovccApi = new WOVCCApi(API_CONFIG);

// Export for use in other scripts
window.WOVCCApi = wovccApi;

