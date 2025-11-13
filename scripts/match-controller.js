(function () {
    "use strict";
    const DEBUG_MATCH =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1" ||
        !window.location.hostname;
    const debugMatch = {
        log: (...args) => DEBUG_MATCH && console.log(...args),
        warn: (...args) => DEBUG_MATCH && console.warn(...args),
        error: (...args) => console.error(...args),
        info: (...args) => DEBUG_MATCH && console.info(...args),
    };
    class MatchController {
        constructor() {
            this.liveSection = document.getElementById("live-match-section");
            this.noMatchSection = document.getElementById("no-match-section");
            this.fixturesContainer = document.getElementById("upcoming-fixtures-container");
            this.resultsContainer = document.getElementById("recent-results-container");
            this.teamSelector = document.getElementById("team-selector");
            this.currentTeam = "all";
            this.pollInterval = null;
            this.initialized = false;
        }
        async init() {
            if (this.initialized) {
                // Re-initialize if already initialized (for page transitions)
                this.cleanup();
            }
            
            // Scroll to top immediately when initializing match page
            window.scrollTo(0, 0);
            
            // Re-get elements in case of page transition
            this.liveSection = document.getElementById("live-match-section");
            this.noMatchSection = document.getElementById("no-match-section");
            this.fixturesContainer = document.getElementById("upcoming-fixtures-container");
            this.resultsContainer = document.getElementById("recent-results-container");
            this.teamSelector = document.getElementById("team-selector");
            
            await this.setupTeamSelector();
            await this.checkMatchStatus();
            await this.loadData();
            this.startPolling();
            this.initialized = true;
        }
        
        cleanup() {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
            this.initialized = false;
        }
        async setupTeamSelector() {
            if (!this.teamSelector) return;
            this.teamSelector.style.opacity = "0.6";
            this.teamSelector.disabled = true;
            try {
                const teams = await wovccApi.getTeams();
                this.teamSelector.innerHTML = '<option value="all">All Teams</option>';
                teams.forEach((team) => {
                    const option = document.createElement("option");
                    option.value = team.id;
                    option.textContent = team.name;
                    this.teamSelector.appendChild(option);
                });
                this.teamSelector.addEventListener("change", () => {
                    this.currentTeam = this.teamSelector.value;
                    this.loadData();
                });
                this.teamSelector.style.opacity = "1";
                this.teamSelector.disabled = false;
            } catch (error) {
                debugMatch.error("Failed to setup team selector: ", error);
                this.teamSelector.style.opacity = "1";
                this.teamSelector.disabled = false;
            }
        }
        async checkMatchStatus() {
            try {
                const response = await fetch(`${wovccApi.baseURL}/live-config`);
                const data = await response.json();
                if (data.success && data.config) {
                    const config = data.config;
                    if (config.is_live && config.selected_match) {
                        const todaysMatches = await this.getTodaysMatches();
                        if (config.livestream_url && config.livestream_url.trim() !== "") {
                            this.showExternalLivestream(config.livestream_url, config.selected_match);
                        } else {
                            this.hideExternalLivestream();
                        }
                        if (todaysMatches.length > 0) {
                            this.injectMultiplePlayCricketWidgets(todaysMatches);
                        }
                        this.showLiveSection();
                    } else {
                        this.showNoMatchSection();
                    }
                } else {
                    this.showNoMatchSection();
                }
            } catch (error) {
                debugMatch.error("Failed to check match status:", error);
                this.showNoMatchSection();
            }
        }
        async getTodaysMatches() {
            try {
                const fixtures = await wovccApi.getFixtures("all");
                const today = new Date().toISOString().split("T")[0];
                const todaysMatches = fixtures.filter((f) => f.date_iso === today);
                return todaysMatches;
            } catch (error) {
                debugMatch.error("Failed to get todays matches: ", error);
                return [];
            }
        }
        injectMultiplePlayCricketWidgets(matches) {
            const container = document.getElementById("live-scores-widgets-container");
            if (!container || !matches || matches.length === 0) return;
            container.innerHTML = "";
            matches.forEach((match, index) => {
                const teamId = match.team_id;
                if (!teamId) return;
                const uniqueId = Date.now() + index;
                const linkId = `lsw_link_${uniqueId}`;
                const containerId = `lsw_container_${uniqueId}`;
                const widgetWrapper = document.createElement("div");
                widgetWrapper.style.cssText = "margin-bottom:30px;";
                const matchTitle = document.createElement("h4");
                matchTitle.style.cssText = "color:var(--primary-color);margin-bottom:15px;font-size:1.1rem;";
                matchTitle.textContent = `${match.team_name_scraping} - ${match.home_team} vs ${match.away_team}`;
                widgetWrapper.appendChild(matchTitle);
                const widgetHTML = `<a style="display:none;" class="lsw" href="https://www.play-cricket.com/embed_widget/live_scorer_widgets?team_id=${teamId}&days=0" id="${linkId}"></a><div class="lsw-col-12 lsw_tile" id="${containerId}"></div>`;
                const widgetDiv = document.createElement("div");
                widgetDiv.innerHTML = widgetHTML;
                widgetWrapper.appendChild(widgetDiv);
                container.appendChild(widgetWrapper);
            });
            this.loadPlayCricketResources();
        }
        loadPlayCricketResources() {
            if (!document.querySelector('link[href="https://www.play-cricket.com/live_scorer.css"]')) {
                const cssLink = document.createElement("link");
                cssLink.rel = "stylesheet";
                cssLink.href = "https://www.play-cricket.com/live_scorer.css";
                document.head.appendChild(cssLink);
            }
            if (!document.getElementById("lsw-wjs")) {
                const script = document.createElement("script");
                script.id = "lsw-wjs";
                script.src = "https://www.play-cricket.com/live_scorer.js";
                script.async = true;
                document.body.appendChild(script);
            } else {
                if (window.LSW && window.LSW.refresh) {
                    window.LSW.refresh();
                }
            }
        }
        showExternalLivestream(url, match) {
            const container = document.getElementById("external-livestream-container");
            const iframe = document.getElementById("external-livestream-player");
            const titleElement = document.getElementById("livestream-match-title");
            if (container && iframe && url) {
                iframe.src = url;
                container.style.display = "block";
                if (titleElement && match) {
                    titleElement.textContent = `Live Stream-${match.team_name_scraping}:${match.home_team}vs ${match.away_team}`;
                }
            }
        }
        hideExternalLivestream() {
            const container = document.getElementById("external-livestream-container");
            const iframe = document.getElementById("external-livestream-player");
            if (container) {
                container.style.display = "none";
            }
            if (iframe) {
                iframe.src = "";
            }
        }
        async loadData() {
            await Promise.all([this.loadFixtures(), this.loadResults()]);
            const lastUpdatedContainer = document.getElementById("last-updated-container");
            if (lastUpdatedContainer) {
                wovccApi.renderLastUpdated(lastUpdatedContainer);
            }
        }
        async loadFixtures() {
            if (!this.fixturesContainer) return;
            wovccApi.renderFixturesSkeleton(this.fixturesContainer, 2);
            try {
                const fixtures = await wovccApi.getFixtures(this.currentTeam);
                wovccApi.renderFixtures(fixtures, this.fixturesContainer, 2);
            } catch (error) {
                debugMatch.error("Failed to load fixtures:", error);
                this.fixturesContainer.innerHTML = `<p style="text-align:center;color:var(--text-light);padding:40px;">Failed to load fixtures. Please try again later.</p>`;
            }
        }
        async loadResults() {
            if (!this.resultsContainer) return;
            wovccApi.renderResultsSkeleton(this.resultsContainer, 2);
            try {
                const results = await wovccApi.getResults(this.currentTeam, 10);
                wovccApi.renderResults(results, this.resultsContainer, 2);
            } catch (error) {
                debugMatch.error("Failed to load results:", error);
                this.resultsContainer.innerHTML = `<p style="text-align:center;color:var(--text-light);padding:40px;">Failed to load results. Please try again later.</p>`;
            }
        }
        showLiveSection() {
            if (this.liveSection && this.noMatchSection) {
                this.liveSection.style.display = "block";
                this.noMatchSection.style.display = "none";
            }
        }
        showNoMatchSection() {
            if (this.liveSection && this.noMatchSection) {
                this.liveSection.style.display = "none";
                this.noMatchSection.style.display = "block";
            }
        }
        startPolling() {
            this.pollInterval = setInterval(
                () => {
                    this.checkMatchStatus();
                },
                5 * 60 * 1000
            );
        }
        stopPolling() {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
        }
    }
    
    // Initialize function for page transitions
    let matchdayInitialized = false;
    
    window.initializeMatchday = async function() {
        // Prevent double initialization
        if (matchdayInitialized) return;
        matchdayInitialized = true;
        
        const controller = new MatchController();
        window.matchController = controller;
        await controller.init();
    };
    
    // Initialize immediately if DOM is already loaded, otherwise wait
    const init = async () => {  
        await window.initializeMatchday();  
    };  

    if (document.readyState === 'loading') {  
        document.addEventListener("DOMContentLoaded", init);  
    } else {  
        // DOM is already loaded (page transition scenario)  
        init();  
    }  
    
    // Re-initialize on page transitions
    document.addEventListener("pageTransitionComplete", async function(e) {
        if (e.detail.path === '/') {
            matchdayInitialized = false; // Reset flag for new page load
            await window.initializeMatchday();
        }
    });
    
    window.addEventListener("beforeunload", function () {
        if (window.matchController) {
            window.matchController.stopPolling();
        }
    });
    window.MatchController = MatchController;
})();
