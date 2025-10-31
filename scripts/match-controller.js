// ===================================
// WOVCC Match Controller
// Controls display of live matches vs fixtures/results
// ===================================

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
      
    } catch (error) {
      console.error('Failed to setup team selector:', error);
    }
  }
  
  /**
   * Check if matches are happening today
   */
  async checkMatchStatus() {
    try {
      const hasMatches = await wovccApi.checkMatchStatus();
      
      if (hasMatches) {
        this.showLiveSection();
      } else {
        this.showNoMatchSection();
      }
      
    } catch (error) {
      console.error('Failed to check match status:', error);
      // Default to showing no-match section on error
      this.showNoMatchSection();
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
  }
  
  /**
   * Load fixtures
   */
  async loadFixtures() {
    if (!this.fixturesContainer) return;
    
    try {
      const fixtures = await wovccApi.getFixtures(this.currentTeam);
      wovccApi.renderFixtures(fixtures, this.fixturesContainer);
    } catch (error) {
      console.error('Failed to load fixtures:', error);
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
    
    try {
      const results = await wovccApi.getResults(this.currentTeam, 10);
      wovccApi.renderResults(results, this.resultsContainer);
    } catch (error) {
      console.error('Failed to load results:', error);
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

