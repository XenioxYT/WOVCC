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
    console.log('Local cache cleared');
  }
  
  /**
   * Force refresh the data from the API
   */
  async refreshData() {
    this.clearCache();
    return await this._fetchAllData();
  }
  
  /**
   * Render fixtures to a container element
   * @param {Array} fixtures - Fixtures data
   * @param {HTMLElement} container - Container element
   */
  renderFixtures(fixtures, container) {
    if (!container) return;
    
    if (!fixtures || fixtures.length === 0) {
      container.innerHTML = `
        <p style="text-align: center; color: var(--text-light); padding: 40px;">
          No upcoming fixtures found.
        </p>
      `;
      // Hide show more button
      const showMoreContainer = document.getElementById('fixtures-show-more-container');
      if (showMoreContainer) {
        showMoreContainer.style.display = 'none';
      }
      return;
    }
    
    const INITIAL_DISPLAY = 3;
    let html = '';
    
    fixtures.forEach((fixture, index) => {
      const timeText = fixture.time ? `${fixture.time}` : '';
      const locationText = fixture.location ? `${fixture.location}` : '';
      const matchUrl = fixture.match_url || '#';
      const isHidden = index >= INITIAL_DISPLAY;
      
      html += `
        <a href="${matchUrl}" target="_blank" class="fixture-card-link fixture-item" style="text-decoration: none; color: inherit; display: ${isHidden ? 'none' : 'block'};">
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
    
    // Handle show more button
    const showMoreContainer = document.getElementById('fixtures-show-more-container');
    const showMoreBtn = document.getElementById('fixtures-show-more-btn');
    
    if (fixtures.length > INITIAL_DISPLAY) {
      if (showMoreContainer) {
        showMoreContainer.style.display = 'block';
      }
      
      if (showMoreBtn) {
        // Remove old event listeners by cloning and replacing
        const newBtn = showMoreBtn.cloneNode(true);
        showMoreBtn.parentNode.replaceChild(newBtn, showMoreBtn);
        
        newBtn.addEventListener('click', () => {
          const hiddenItems = container.querySelectorAll('.fixture-item[style*="display: none"]');
          hiddenItems.forEach(item => {
            item.style.display = 'block';
          });
          newBtn.parentElement.style.display = 'none';
        });
      }
    } else {
      if (showMoreContainer) {
        showMoreContainer.style.display = 'none';
      }
    }
  }
  
  /**
   * Render results to a container element
   * @param {Array} results - Results data
   * @param {HTMLElement} container - Container element
   */
  renderResults(results, container) {
    if (!container) return;
    
    if (!results || results.length === 0) {
      container.innerHTML = `
        <p style="text-align: center; color: var(--text-light); padding: 40px;">
          No recent results found.
        </p>
      `;
      // Hide show more button
      const showMoreContainer = document.getElementById('results-show-more-container');
      if (showMoreContainer) {
        showMoreContainer.style.display = 'none';
      }
      return;
    }
    
    const INITIAL_DISPLAY = 3;
    let html = '';
    
    results.forEach((result, index) => {
      const resultClass = result.is_win ? 'win' : result.is_loss ? 'loss' : 'draw';
      const matchUrl = result.match_url || '#';
      const resultLabel = result.is_win ? 'Won' : result.is_loss ? 'Lost' : 'Draw';
      const isHidden = index >= INITIAL_DISPLAY;
      
      html += `
        <a href="${matchUrl}" target="_blank" class="result-card-link result-item" style="text-decoration: none; color: inherit; display: ${isHidden ? 'none' : 'block'};">
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
    
    // Handle show more button
    const showMoreContainer = document.getElementById('results-show-more-container');
    const showMoreBtn = document.getElementById('results-show-more-btn');
    
    if (results.length > INITIAL_DISPLAY) {
      if (showMoreContainer) {
        showMoreContainer.style.display = 'block';
      }
      
      if (showMoreBtn) {
        // Remove old event listeners by cloning and replacing
        const newBtn = showMoreBtn.cloneNode(true);
        showMoreBtn.parentNode.replaceChild(newBtn, showMoreBtn);
        
        newBtn.addEventListener('click', () => {
          const hiddenItems = container.querySelectorAll('.result-item[style*="display: none"]');
          hiddenItems.forEach(item => {
            item.style.display = 'block';
          });
          newBtn.parentElement.style.display = 'none';
        });
      }
    } else {
      if (showMoreContainer) {
        showMoreContainer.style.display = 'none';
      }
    }
  }
}

// Initialize API client
const wovccApi = new WOVCCApi(API_CONFIG);

// Export for use in other scripts
window.WOVCCApi = wovccApi;

