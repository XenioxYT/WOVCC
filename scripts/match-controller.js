// ===================================
// WOVCC Match Controller
// Controls display of live matches vs fixtures/results
// ===================================

// Debug utility - only logs in development
const DEBUG = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || !window.location.hostname;
const debug = {
  log: (...args) => DEBUG && console.log(...args),
  warn: (...args) => DEBUG && console.warn(...args),
  error: (...args) => console.error(...args), // Always log errors
  info: (...args) => DEBUG && console.info(...args)
};

class MatchController {
  constructor() {
    this.liveSection = document.getElementById('live-match-section');
    this.noMatchSection = document.getElementById('no-match-section');
    this.fixturesContainer = document.getElementById('upcoming-fixtures-container');
    this.resultsContainer = document.getElementById('recent-results-container');
    this.teamSelector = document.getElementById('team-selector');
    
    this.currentTeam = 'all';
    this.pollInterval = null;
    this.initialized = false;
  }
  
  /**
   * Initialize the controller
   */
  async init() {
    if (this.initialized) return;
    
    // Setup team selector
    await this.setupTeamSelector();
    
    // Check initial match status
    await this.checkMatchStatus();
    
    // Load fixtures and results
    await this.loadData();
    
    // Start polling every 5 minutes
    this.startPolling();
    
    this.initialized = true;
  }
  
  /**
   * Setup team selector dropdown
   */
  async setupTeamSelector() {
    if (!this.teamSelector) return;
    
    // Show loading state
    this.teamSelector.style.opacity = '0.6';
    this.teamSelector.disabled = true;
    
    try {
      const teams = await wovccApi.getTeams();
      
      // Clear existing options (except "All Teams")
      this.teamSelector.innerHTML = '<option value="all">All Teams</option>';
      
      // Add team options
      teams.forEach(team => {
        const option = document.createElement('option');
        option.value = team.id;
        option.textContent = team.name;
        this.teamSelector.appendChild(option);
      });
      
      // Setup change handler
      this.teamSelector.addEventListener('change', () => {
        this.currentTeam = this.teamSelector.value;
        this.loadData();
      });
      
      // Restore selector
      this.teamSelector.style.opacity = '1';
      this.teamSelector.disabled = false;
      
    } catch (error) {
      debug.error('Failed to setup team selector:', error);
      this.teamSelector.style.opacity = '1';
      this.teamSelector.disabled = false;
    }
  }
  
  /**
   * Check live match configuration from admin panel
   */
  async checkMatchStatus() {
    try {
      // Get live configuration from API
      const response = await fetch(`${wovccApi.baseURL}/live-config`);
      const data = await response.json();
      
      if (data.success && data.config) {
        const config = data.config;
        
        // Check if admin has enabled live section
        if (config.is_live && config.selected_match) {
          // Get all today's matches
          const todaysMatches = await this.getTodaysMatches();
          
          // Show/hide external livestream if provided (for primary match only)
          if (config.livestream_url && config.livestream_url.trim() !== '') {
            this.showExternalLivestream(config.livestream_url, config.selected_match);
          } else {
            this.hideExternalLivestream();
          }
          
          // Inject Play-Cricket widgets for all today's matches
          if (todaysMatches.length > 0) {
            this.injectMultiplePlayCricketWidgets(todaysMatches);
          }
          
          // Show live section
          this.showLiveSection();
        } else {
          // Show regular fixtures/results section
          this.showNoMatchSection();
        }
      } else {
        // Default to showing no-match section
        this.showNoMatchSection();
      }
      
    } catch (error) {
      debug.error('Failed to check match status:', error);
      // Default to showing no-match section on error
      this.showNoMatchSection();
    }
  }
  
  /**
   * Get all fixtures scheduled for today
   */
  async getTodaysMatches() {
    try {
      const fixtures = await wovccApi.getFixtures('all');
      
      // Get today's date in ISO format (YYYY-MM-DD)
      const today = new Date().toISOString().split('T')[0];
      
      // Filter fixtures for today
      const todaysMatches = fixtures.filter(f => f.date_iso === today);
      
      return todaysMatches;
    } catch (error) {
      debug.error('Failed to get todays matches:', error);
      return [];
    }
  }
  
  /**
   * Inject multiple Play-Cricket live score widgets for today's matches
   */
  injectMultiplePlayCricketWidgets(matches) {
    const container = document.getElementById('live-scores-widgets-container');
    if (!container || !matches || matches.length === 0) return;
    
    // Clear any existing content
    container.innerHTML = '';
    
    // Create a widget for each match
    matches.forEach((match, index) => {
      const teamId = match.team_id;
      if (!teamId) return;
      
      // Generate unique IDs for this widget instance
      const uniqueId = Date.now() + index;
      const linkId = `lsw_link_${uniqueId}`;
      const containerId = `lsw_container_${uniqueId}`;
      
      // Create a wrapper for each widget with match info
      const widgetWrapper = document.createElement('div');
      widgetWrapper.style.cssText = 'margin-bottom: 30px;';
      
      // Add match title
      const matchTitle = document.createElement('h4');
      matchTitle.style.cssText = 'color: var(--primary-color); margin-bottom: 15px; font-size: 1.1rem;';
      matchTitle.textContent = `${match.team_name_scraping} - ${match.home_team} vs ${match.away_team}`;
      widgetWrapper.appendChild(matchTitle);
      
      // Create the Play-Cricket widget HTML
      const widgetHTML = `
        <a style="display:none;" class="lsw" href="https://www.play-cricket.com/embed_widget/live_scorer_widgets?team_id=${teamId}&days=0" id="${linkId}"></a>
        <div class="lsw-col-12 lsw_tile" id="${containerId}"></div>
      `;
      
      const widgetDiv = document.createElement('div');
      widgetDiv.innerHTML = widgetHTML;
      widgetWrapper.appendChild(widgetDiv);
      
      container.appendChild(widgetWrapper);
    });
    
    // Load the CSS and JavaScript for the widgets
    this.loadPlayCricketResources();
  }
  
  /**
   * Load Play-Cricket CSS and JavaScript resources
   */
  loadPlayCricketResources() {
    // Load CSS if not already loaded
    if (!document.querySelector('link[href="https://www.play-cricket.com/live_scorer.css"]')) {
      const cssLink = document.createElement('link');
      cssLink.rel = 'stylesheet';
      cssLink.href = 'https://www.play-cricket.com/live_scorer.css';
      document.head.appendChild(cssLink);
    }
    
    // Load JavaScript if not already loaded
    if (!document.getElementById('lsw-wjs')) {
      const script = document.createElement('script');
      script.id = 'lsw-wjs';
      script.src = 'https://www.play-cricket.com/live_scorer.js';
      script.async = true;
      document.body.appendChild(script);
    } else {
      // If script already loaded, trigger refresh
      if (window.LSW && window.LSW.refresh) {
        window.LSW.refresh();
      }
    }
  }
  
  /**
   * Show external livestream iframe with match name
   */
  showExternalLivestream(url, match) {
    const container = document.getElementById('external-livestream-container');
    const iframe = document.getElementById('external-livestream-player');
    const titleElement = document.getElementById('livestream-match-title');
    
    if (container && iframe && url) {
      iframe.src = url;
      container.style.display = 'block';
      
      // Update title with match info if available
      if (titleElement && match) {
        titleElement.textContent = `Live Stream - ${match.team_name_scraping}: ${match.home_team} vs ${match.away_team}`;
      }
    }
  }
  
  /**
   * Hide external livestream iframe
   */
  hideExternalLivestream() {
    const container = document.getElementById('external-livestream-container');
    const iframe = document.getElementById('external-livestream-player');
    
    if (container) {
      container.style.display = 'none';
    }
    
    if (iframe) {
      iframe.src = '';
    }
  }
  
  /**
   * Load fixtures and results data
   */
  async loadData() {
    await Promise.all([
      this.loadFixtures(),
      this.loadResults()
    ]);
    
    // Display last updated timestamp
    const lastUpdatedContainer = document.getElementById('last-updated-container');
    if (lastUpdatedContainer) {
      wovccApi.renderLastUpdated(lastUpdatedContainer);
    }
  }
  
  /**
   * Load fixtures
   */
  async loadFixtures() {
    if (!this.fixturesContainer) return;
    
    // Show skeleton loader while loading
    wovccApi.renderFixturesSkeleton(this.fixturesContainer, 2);
    
    try {
      const fixtures = await wovccApi.getFixtures(this.currentTeam);
      // Limit to 2 fixtures for homepage
      wovccApi.renderFixtures(fixtures, this.fixturesContainer, 2);
    } catch (error) {
      debug.error('Failed to load fixtures:', error);
      this.fixturesContainer.innerHTML = `
        <p style="text-align: center; color: var(--text-light); padding: 40px;">
          Failed to load fixtures. Please try again later.
        </p>
      `;
    }
  }
  
  /**
   * Load results
   */
  async loadResults() {
    if (!this.resultsContainer) return;
    
    // Show skeleton loader while loading
    wovccApi.renderResultsSkeleton(this.resultsContainer, 2);
    
    try {
      const results = await wovccApi.getResults(this.currentTeam, 10);
      // Limit to 2 results for homepage
      wovccApi.renderResults(results, this.resultsContainer, 2);
    } catch (error) {
      debug.error('Failed to load results:', error);
      this.resultsContainer.innerHTML = `
        <p style="text-align: center; color: var(--text-light); padding: 40px;">
          Failed to load results. Please try again later.
        </p>
      `;
    }
  }
  
  /**
   * Show live match section
   */
  showLiveSection() {
    if (this.liveSection && this.noMatchSection) {
      this.liveSection.style.display = 'block';
      this.noMatchSection.style.display = 'none';
    }
  }
  
  /**
   * Show no-match section
   */
  showNoMatchSection() {
    if (this.liveSection && this.noMatchSection) {
      this.liveSection.style.display = 'none';
      this.noMatchSection.style.display = 'block';
    }
  }
  
  /**
   * Start polling for match status
   */
  startPolling() {
    // Poll every 5 minutes
    this.pollInterval = setInterval(() => {
      this.checkMatchStatus();
    }, 5 * 60 * 1000);
  }
  
  /**
   * Stop polling
   */
  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
}

// Initialize match controller when page loads
document.addEventListener('DOMContentLoaded', async function() {
  // Wait a bit for API client to be ready
  setTimeout(async () => {
    const controller = new MatchController();
    await controller.init();
  }, 100);
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
  if (window.matchController) {
    window.matchController.stopPolling();
  }
});


