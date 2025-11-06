/**
 * Performance Monitoring Client
 * Logs performance metrics from server response headers
 */

class PerformanceMonitor {
    constructor() {
        this.metrics = [];
        this.enabled = localStorage.getItem('perf_monitor_enabled') === 'true';
        
        if (this.enabled) {
            this.init();
        }
    }

    init() {
        console.log('%c🚀 Performance Monitor Enabled', 'color: #00ff00; font-weight: bold; font-size: 14px;');
        console.log('Performance metrics will be logged for each request.');
        console.log('To disable: localStorage.setItem("perf_monitor_enabled", "false") and reload');
        
        // Intercept fetch requests
        this.interceptFetch();
    }

    interceptFetch() {
        const originalFetch = window.fetch;
        const self = this;

        window.fetch = function(...args) {
            const startTime = performance.now();
            const url = args[0];

            return originalFetch.apply(this, args).then(response => {
                const endTime = performance.now();
                const clientTime = endTime - startTime;

                // Extract performance headers
                const serverTime = response.headers.get('X-Response-Time');
                const dbQueries = response.headers.get('X-DB-Queries');
                const dbTime = response.headers.get('X-DB-Time');

                if (serverTime) {
                    const metric = {
                        url: url,
                        clientTime: clientTime.toFixed(2),
                        serverTime: serverTime,
                        dbQueries: dbQueries || '0',
                        dbTime: dbTime || '0ms',
                        status: response.status,
                        timestamp: new Date().toISOString()
                    };

                    self.metrics.push(metric);
                    self.logMetric(metric);
                }

                return response;
            });
        };
    }

    logMetric(metric) {
        const serverMs = parseFloat(metric.serverTime);
        const clientMs = parseFloat(metric.clientTime);
        const networkMs = clientMs - serverMs;

        // Color code based on performance
        let color = '#00ff00'; // Green for fast
        if (serverMs > 500) {
            color = '#ff0000'; // Red for slow
        } else if (serverMs > 200) {
            color = '#ffaa00'; // Orange for medium
        }

        console.groupCollapsed(
            `%c⚡ ${metric.url}`,
            `color: ${color}; font-weight: bold;`
        );
        console.log(`Status: ${metric.status}`);
        console.log(`Client Time: ${metric.clientTime}ms (total including network)`);
        console.log(`Server Time: ${metric.serverTime}`);
        console.log(`Network Time: ~${networkMs.toFixed(2)}ms`);
        console.log(`DB Queries: ${metric.dbQueries}`);
        console.log(`DB Time: ${metric.dbTime}`);
        
        if (serverMs > 500) {
            console.warn('⚠️ SLOW REQUEST - Consider optimization');
        }
        
        console.groupEnd();
    }

    getStats() {
        if (this.metrics.length === 0) {
            console.log('No metrics collected yet');
            return;
        }

        const serverTimes = this.metrics.map(m => parseFloat(m.serverTime));
        const avgServerTime = (serverTimes.reduce((a, b) => a + b, 0) / serverTimes.length).toFixed(2);
        const maxServerTime = Math.max(...serverTimes).toFixed(2);
        const minServerTime = Math.min(...serverTimes).toFixed(2);

        console.group('📊 Performance Statistics');
        console.log(`Total Requests: ${this.metrics.length}`);
        console.log(`Average Server Time: ${avgServerTime}ms`);
        console.log(`Min Server Time: ${minServerTime}ms`);
        console.log(`Max Server Time: ${maxServerTime}ms`);
        console.log(`Slowest Request:`, this.metrics.find(m => parseFloat(m.serverTime) === parseFloat(maxServerTime)));
        console.groupEnd();

        return {
            totalRequests: this.metrics.length,
            avgServerTime: avgServerTime,
            maxServerTime: maxServerTime,
            minServerTime: minServerTime
        };
    }

    clear() {
        this.metrics = [];
        console.log('Performance metrics cleared');
    }

    export() {
        return JSON.stringify(this.metrics, null, 2);
    }
}

// Enable performance monitoring via console
// To enable: perfMonitor.enable()
// To disable: perfMonitor.disable()
// To view stats: perfMonitor.getStats()
// To clear metrics: perfMonitor.clear()

window.perfMonitor = {
    instance: null,
    
    enable() {
        localStorage.setItem('perf_monitor_enabled', 'true');
        console.log('✅ Performance monitoring enabled. Reload the page to activate.');
    },
    
    disable() {
        localStorage.setItem('perf_monitor_enabled', 'false');
        console.log('❌ Performance monitoring disabled. Reload the page to deactivate.');
    },
    
    getStats() {
        if (this.instance) {
            return this.instance.getStats();
        } else {
            console.log('Performance monitoring is not enabled. Run perfMonitor.enable() and reload.');
        }
    },
    
    clear() {
        if (this.instance) {
            this.instance.clear();
        }
    },
    
    export() {
        if (this.instance) {
            const data = this.instance.export();
            console.log(data);
            return data;
        }
    }
};

// Auto-initialize if enabled
if (localStorage.getItem('perf_monitor_enabled') === 'true') {
    window.perfMonitor.instance = new PerformanceMonitor();
} else {
    console.log(
        '%c💡 Performance Monitoring Available',
        'color: #00aaff; font-weight: bold; font-size: 12px;'
    );
    console.log('To enable performance monitoring, run: perfMonitor.enable()');
}
