(function() {
    'use strict';
    const DEBUG_API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const debugApi = {
        log: (...args) => DEBUG_API && console.log(...args),
        warn: (...args) => DEBUG_API && console.warn(...args),
        error: (...args) => console.error(...args),
        info: (...args) => DEBUG_API && console.info(...args)
    };
    const API_CONFIG = {
        baseURL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:5000/api' : 'https://wovcc.xeniox.uk/api',
        timeout: 10000
    };
    class WOVCCApi {
        constructor(config) {
            this.baseURL = config.baseURL;
            this.timeout = config.timeout;
            this.cachedData = null;
            this.cacheTimestamp = null;
            this.cacheMaxAge = 5 * 60 * 1000;
            this.lastUpdated = null;
        }
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
            if (diffMin < 60) return `${diffMin} minute${diffMin!==1?'s':''} ago`;
            if (diffHour < 24) return `${diffHour} hour${diffHour!==1?'s':''} ago`;
            if (diffDay < 7) return `${diffDay} day${diffDay!==1?'s':''} ago`;
            return then.toLocaleDateString('en-GB', {
                day: 'numeric',
                month: 'short',
                year: 'numeric'
            });
        }
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
                    throw new Error(`API Error:${response.status}`);
                }
                return await response.json();
            } catch (error) {
                clearTimeout(timeoutId);
                if (error.name === 'AbortError') {
                    throw new Error('Request timeout');
                }
                console.error(`API Error(${endpoint}):`, error);
                throw error;
            }
        }
        async _fetchAllData() {
            const now = Date.now();
            if (this.cachedData && this.cacheTimestamp && (now - this.cacheTimestamp < this.cacheMaxAge)) {
                debugApi.log('Using cached data');
                return this.cachedData;
            }
            try {
                debugApi.log('Fetching fresh data from API...');
                const data = await this._fetch('/data?source=file');
                if (data.success) {
                    this.cachedData = data;
                    this.cacheTimestamp = now;
                    this.lastUpdated = data.last_updated || null;
                    console.log(`Data fetched successfully(last updated:${data.last_updated})`);
                    return data;
                } else {
                    throw new Error('API returned unsuccessful response');
                }
            } catch (error) {
                debugApi.error('Failed to fetch all data:', error);
                if (this.cachedData) {
                    debugApi.warn('Using stale cached data as fallback');
                    return this.cachedData;
                }
                throw error;
            }
        }
        async healthCheck() {
            try {
                const data = await this._fetch('/health');
                return data;
            } catch (error) {
                debugApi.error('Health check failed:', error);
                return {
                    status: 'error',
                    message: error.message
                };
            }
        }
        async getTeams() {
            try {
                const data = await this._fetchAllData();
                return data.teams || [];
            } catch (error) {
                debugApi.error('Failed to fetch teams:', error);
                return [];
            }
        }
        async getFixtures(teamId = 'all') {
            try {
                const data = await this._fetchAllData();
                let fixtures = data.fixtures || [];
                if (teamId && teamId !== 'all') {
                    fixtures = fixtures.filter(f => f.team_id === teamId || f.team_id === String(teamId));
                }
                fixtures.sort((a, b) => {
                    const dateA = new Date(a.date_iso || a.date_str);
                    const dateB = new Date(b.date_iso || b.date_str);
                    return dateA - dateB;
                });
                return fixtures;
            } catch (error) {
                debugApi.error('Failed to fetch fixtures:', error);
                return [];
            }
        }
        async getResults(teamId = 'all', limit = 10) {
            try {
                const data = await this._fetchAllData();
                let results = data.results || [];
                if (teamId && teamId !== 'all') {
                    results = results.filter(r => r.team_id === teamId || r.team_id === String(teamId));
                }
                results.sort((a, b) => {
                    const dateA = new Date(a.date_iso || a.date_str);
                    const dateB = new Date(b.date_iso || b.date_str);
                    return dateB - dateA;
                });
                if (limit && limit > 0) {
                    results = results.slice(0, limit);
                }
                return results;
            } catch (error) {
                debugApi.error('Failed to fetch results:', error);
                return [];
            }
        }
        async checkMatchStatus() {
            try {
                const data = await this._fetchAllData();
                const fixtures = data.fixtures || [];
                const today = new Date().toISOString().split('T')[0];
                const hasMatchesToday = fixtures.some(f => f.date_iso === today);
                return hasMatchesToday;
            } catch (error) {
                debugApi.error('Failed to check match status:', error);
                return false;
            }
        }
        clearCache() {
            this.cachedData = null;
            this.cacheTimestamp = null;
            this.lastUpdated = null;
            debugApi.log('Local cache cleared');
        }
        renderLastUpdated(container) {
            if (!container) return;
            const lastUpdated = this.getLastUpdated();
            if (!lastUpdated) {
                container.innerHTML = '';
                return;
            }
            container.innerHTML = `<div class="last-updated-display" style="text-align:center;margin-top:15px;padding:10px 0;color:var(--text-light);font-size:0.85rem;"><span style="color:var(--text-light);">Last updated:</span><span class="last-updated-time" style="color:var(--primary-color);font-weight:500;margin-left:5px;cursor:help;" title="${lastUpdated.full}">${lastUpdated.relative}</span></div>`;
        }
        async refreshData() {
            this.clearCache();
            return await this._fetchAllData();
        }
        renderFixturesSkeleton(container, count = 2) {
            if (!container) return;
            let html = '';
            for (let i = 0; i < count; i++) {
                html += `<div class="skeleton-card"><div class="skeleton-loader skeleton-line short" style="margin-bottom:12px;"></div><div class="skeleton-loader skeleton-line medium" style="margin-bottom:8px;"></div><div class="skeleton-loader skeleton-line long" style="margin-bottom:8px;"></div><div style="display:flex;gap:15px;margin-top:12px;"><div class="skeleton-loader skeleton-line short" style="width:100px;height:14px;"></div><div class="skeleton-loader skeleton-line short" style="width:120px;height:14px;"></div></div></div>`;
            }
            container.innerHTML = html;
        }
        renderResultsSkeleton(container, count = 2) {
            if (!container) return;
            let html = '';
            for (let i = 0; i < count; i++) {
                html += `<div class="skeleton-card"><div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;"><div class="skeleton-loader skeleton-line short" style="width:120px;height:16px;"></div><div class="skeleton-loader skeleton-line short" style="width:60px;height:24px;border-radius:12px;"></div></div><div class="skeleton-loader skeleton-line medium" style="margin-bottom:8px;"></div><div class="skeleton-loader skeleton-line long" style="margin-bottom:8px;"></div><div class="skeleton-loader skeleton-line medium" style="width:70%;margin-top:8px;"></div></div>`;
            }
            container.innerHTML = html;
        }
        renderLoadingSpinner(container, message = 'Loading...') {
            if (!container) return;
            container.innerHTML = `<div class="loading-spinner-container"><div class="skeleton-spinner"></div><span>${message}</span></div>`;
        }
        renderFixtures(fixtures, container, limit = null) {
            if (!container) return;
            if (!fixtures || fixtures.length === 0) {
                container.innerHTML = `<p style="text-align:center;color:var(--text-light);padding:40px;">No upcoming fixtures found.</p>`;
                return;
            }
            const displayFixtures = limit ? fixtures.slice(0, limit) : fixtures;
            let html = '';
            displayFixtures.forEach((fixture, index) => {
                const timeText = fixture.time ? `${fixture.time}` : '';
                const locationText = fixture.location ? `${fixture.location}` : '';
                const matchUrlRaw = fixture.match_url || '#';
                let matchUrl = matchUrlRaw;
                let isLiveLink = false;

                // If the match_url already points to a results page, mark as having results
                if (String(matchUrlRaw).includes('/website/results/')) {
                    isLiveLink = true;
                } else {
                    // If it's the legacy match_details?id= pattern, check:
                    // 1. If we have a result entry in cached data
                    // 2. If the match has started based on date_iso + time
                    const m = String(matchUrlRaw).match(/match_details\?id=(\d+)/);
                    if (m && m[1]) {
                        const id = m[1];
                        const hasResult = this.cachedData && Array.isArray(this.cachedData.results) && this.cachedData.results.some(function(r) {
                            if (!r || !r.match_url) return false;
                            const ru = String(r.match_url);
                            return ru.includes(`/website/results/${id}`) || ru.endsWith(`/${id}`) || ru.includes(id);
                        });
                        
                        // Check if match has started based on date and time
                        let matchHasStarted = false;
                        if (fixture.date_iso && fixture.time) {
                            try {
                                // Parse fixture date and time (time format is "HH:MM")
                                const dateParts = fixture.date_iso.split('-'); // YYYY-MM-DD
                                const timeParts = fixture.time.split(':'); // HH:MM
                                if (dateParts.length === 3 && timeParts.length >= 2) {
                                    const matchDate = new Date(
                                        parseInt(dateParts[0], 10),
                                        parseInt(dateParts[1], 10) - 1, // month is 0-indexed
                                        parseInt(dateParts[2], 10),
                                        parseInt(timeParts[0], 10),
                                        parseInt(timeParts[1], 10)
                                    );
                                    const now = new Date();
                                    matchHasStarted = now >= matchDate;
                                }
                            } catch (e) {
                                // If parsing fails, assume match hasn't started
                            }
                        }
                        
                        if (hasResult || matchHasStarted) {
                            matchUrl = `https://wov.play-cricket.com/website/results/${id}`;
                            isLiveLink = true;
                        }
                        // if no result exists yet and match hasn't started, keep original match_details link and do not show badge
                    }
                }

                const liveBadgeHtml = isLiveLink ? '<span class="live-badge" title="Live/results available">LIVE</span>' : '';

                html += `<a href="${matchUrl}" target="_blank" class="fixture-card-link fixture-item" style="text-decoration:none;color:inherit;display:block;"><div class="fixture-card"><div class="fixture-date-mobile" style="font-weight:600;color:var(--primary-color);margin-bottom:12px;font-size:0.9rem;">${fixture.date_str||fixture.date_iso||''}</div><div class="fixture-card-content"><div class="fixture-card-main"><div style="font-weight:600;color:var(--primary-color);margin-bottom:8px;font-size:0.95rem;">${fixture.team_name_scraping||'Team'}${liveBadgeHtml}</div><div style="color:var(--text-dark);margin-bottom:10px;font-size:1.05rem;font-weight:500;"><div style="margin-bottom:4px;"><span style="font-size:0.85rem;color:var(--text-light);font-weight:400;">Home: </span>${fixture.home_team}</div><div><span style="font-size:0.85rem;color:var(--text-light);font-weight:400;">Away: </span>${fixture.away_team}</div></div><div style="display:flex;gap:15px;flex-wrap:wrap;font-size:0.85rem;color:var(--text-light);">${timeText?`<div><svg style="width:14px;height:14px;display:inline-block;margin-right:4px;vertical-align:middle;" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path></svg>${timeText}</div>`:''}${locationText?`<div><svg style="width:14px;height:14px;display:inline-block;margin-right:4px;vertical-align:middle;" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"></path></svg>${locationText}</div>`:''}</div></div><div class="fixture-date-desktop" style="text-align:right;font-size:0.9rem;color:var(--text-light);white-space:nowrap;"><div style="font-weight:600;color:var(--primary-color);">${fixture.date_str||fixture.date_iso||''}</div></div></div></div></a>`;
            });
            container.innerHTML = html;
        }
        renderResults(results, container, limit = null) {
            if (!container) return;
            if (!results || results.length === 0) {
                container.innerHTML = `<p style="text-align:center;color:var(--text-light);padding:40px;">No recent results found.</p>`;
                return;
            }
            const displayResults = limit ? results.slice(0, limit) : results;
            let html = '';
            displayResults.forEach((result, index) => {
                const resultClass = result.is_win ? 'win' : result.is_loss ? 'loss' : 'draw';
                const matchUrl = result.match_url || '#';
                const resultLabel = result.is_win ? 'Won' : result.is_loss ? 'Lost' : 'Draw';
                html += `<a href="${matchUrl}" target="_blank" class="result-card-link result-item" style="text-decoration:none;color:inherit;display:block;"><div class="result-card ${resultClass}"><div class="fixture-date-mobile" style="font-weight:600;color:var(--primary-color);margin-bottom:12px;font-size:0.9rem;">${result.date_str||result.date_iso||''}</div><div class="fixture-card-content"><div class="fixture-card-main"><div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;"><span style="font-weight:600;color:var(--primary-color);font-size:0.95rem;">${result.team_name_scraping||'Team'}</span><span style="font-size:0.8rem;font-weight:600;padding:3px 10px;border-radius:12px;${result.is_win?'background:#d4edda;color:#155724;':result.is_loss?'background:#f8d7da;color:#721c24;':'background:#fff3cd;color:#856404;'}">${resultLabel}</span></div><div style="color:var(--text-dark);margin-bottom:8px;font-size:1.05rem;font-weight:500;"><div style="margin-bottom:4px;"><span style="font-size:0.85rem;color:var(--text-light);font-weight:400;">Home: </span>${result.home_team} | ${result.home_score?`<strong>${result.home_score}</strong>`:''}</div><div><span style="font-size:0.85rem;color:var(--text-light);font-weight:400;">Away: </span>${result.away_team} | ${result.away_score?`<strong>${result.away_score}</strong>`:''}</div></div>${result.summary?`<div style="font-size:0.88rem;color:var(--text-light);line-height:1.4;margin-top:4px;">${result.summary}</div>`:''}</div><div class="fixture-date-desktop" style="text-align:right;font-size:0.9rem;color:var(--text-light);white-space:nowrap;"><div style="font-weight:600;color:var(--primary-color);">${result.date_str||result.date_iso||''}</div></div></div></div></a>`;
            });
            container.innerHTML = html;
        }
    }
    const wovccApi = new WOVCCApi(API_CONFIG);
    window.wovccApi = wovccApi;
    window.WOVCCApi = WOVCCApi;
})();