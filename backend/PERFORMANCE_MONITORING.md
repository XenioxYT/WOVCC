# Performance Monitoring Guide

This guide explains how to use the performance monitoring features added to the WOVCC application.

## Overview

The application now includes comprehensive performance logging that tracks:
- **Total request time** - End-to-end time for each request
- **Application time** - Time spent in Python code
- **Database time** - Time spent executing database queries
- **Database query count** - Number of queries per request
- **Template rendering time** - Time to render Jinja2 templates
- **Scraper time** - Time spent fetching cricket data

## Server-Side Logging

### Automatic Request Logging

Every HTTP request is automatically logged with performance metrics:

```
2025-11-05 23:40:04 - performance - INFO - GET /api/events | Total: 45.23ms | App: 40.12ms | DB: 5.11ms (1 queries) | Status: 200
```

### Log Format

```
METHOD PATH | Total: XXms | App: XXms | DB: XXms (N queries) | Status: CODE
```

### Slow Request Warnings

Requests taking longer than 500ms are flagged with a warning:

```
2025-11-05 23:40:04 - performance - WARNING - GET /api/data | Total: 850.45ms | App: 120.30ms | DB: 730.15ms (5 queries) | Status: 200 ⚠️ SLOW REQUEST
```

### Response Headers

Every response includes performance headers for client-side monitoring:

- `X-Response-Time: 45.23ms` - Total server processing time
- `X-DB-Queries: 3` - Number of database queries executed
- `X-DB-Time: 15.50ms` - Total time spent on database queries

## Client-Side Monitoring

### Enabling in Browser

The application includes a JavaScript performance monitor. To enable it:

1. Open browser console (F12)
2. Run: `perfMonitor.enable()`
3. Reload the page

### Viewing Metrics

Once enabled, every API request will log performance data:

```
⚡ /api/events
  Status: 200
  Client Time: 52.30ms (total including network)
  Server Time: 45.23ms
  Network Time: ~7.07ms
  DB Queries: 1
  DB Time: 5.11ms
```

### Performance Commands

```javascript
// Enable monitoring (requires page reload)
perfMonitor.enable()

// Disable monitoring (requires page reload)
perfMonitor.disable()

// View aggregate statistics
perfMonitor.getStats()
// Returns: {
//   totalRequests: 15,
//   avgServerTime: "42.50ms",
//   maxServerTime: "850.45ms",
//   minServerTime: "8.12ms"
// }

// Clear collected metrics
perfMonitor.clear()

// Export metrics as JSON
perfMonitor.export()
```

### Color Coding

Requests are color-coded based on performance:
- 🟢 **Green** (0-200ms): Fast, optimal performance
- 🟠 **Orange** (200-500ms): Moderate, room for improvement
- 🔴 **Red** (>500ms): Slow, needs optimization

## Optimization Workflow

### 1. Identify Slow Requests

Run your application and look for:
- ⚠️ SLOW REQUEST warnings in server logs
- Red-colored entries in browser console

### 2. Analyze the Bottleneck

Check the performance breakdown:

```
Total: 850ms
  ├─ App Time: 120ms (14%)
  └─ DB Time: 730ms (86%) ← Problem here!
```

**If DB time is high:**
- Add database indexes
- Optimize queries
- Implement caching
- Reduce number of queries

**If App time is high:**
- Profile Python code
- Optimize algorithms
- Cache computed results
- Reduce template complexity

**If both are low but total is high:**
- Network latency
- Middleware overhead
- Static asset loading

### 3. Common Optimizations

#### Database Optimization
```python
# Add indexes
from sqlalchemy import Index
Index('idx_event_date', Event.date)
Index('idx_event_published', Event.is_published)

# Use eager loading
query = db.query(Event).options(
    joinedload(Event.creator),
    joinedload(Event.interests)
)

# Implement caching
from flask_caching import Cache
cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@cache.cached(timeout=300)
def get_events_cached():
    return get_events()
```

#### Application Optimization
```python
# Use pagination
query = query.limit(50).offset(page * 50)

# Minimize data returned
query = db.query(Event.id, Event.title, Event.date)  # Only needed fields

# Defer expensive operations
@after_response
def send_email():
    # Sends after response is returned
    pass
```

## Viewing Logs

### Real-time Monitoring

```bash
# Watch logs in real-time (Windows PowerShell)
cd C:\Users\tomlo\Documents\WOVCC\backend
python app.py | Select-String -Pattern "performance|SLOW"

# Or in Linux/Mac
python app.py | grep -E "performance|SLOW"
```

### Log Analysis

```bash
# Find slowest requests
Get-Content app.log | Select-String "SLOW REQUEST"

# Average response time
Get-Content app.log | Select-String "Total:" | ForEach-Object {
    if ($_ -match "Total: (\d+\.\d+)ms") {
        [float]$matches[1]
    }
} | Measure-Object -Average
```

## Performance Targets

### Recommended Response Times

| Endpoint Type | Target | Maximum |
|--------------|--------|---------|
| Static files | <50ms | 100ms |
| Simple API | <100ms | 200ms |
| Database query | <200ms | 500ms |
| Complex operation | <500ms | 1000ms |
| File upload | <2000ms | 5000ms |

### Database Query Limits

- **API endpoints**: 1-3 queries per request
- **Page loads**: 3-5 queries per request
- **Admin operations**: Up to 10 queries acceptable

## Integration with Frontend

To automatically log performance for all requests, add to your HTML:

```html
<script src="/scripts/performance-monitor.js"></script>
```

This script will:
- Auto-enable if previously enabled
- Log all fetch requests with metrics
- Provide console commands for analysis
- Persist settings across page loads

## Production Considerations

### Log Level

In production, set log level to WARNING to only log slow requests:

```python
perf_logger.setLevel(logging.WARNING)
```

### APM Integration

For production monitoring, consider integrating:
- New Relic
- DataDog
- Sentry Performance
- AWS X-Ray

### Disable Client Monitoring

In production, you may want to disable client-side performance monitoring for regular users and only enable it for admins or during debugging.

## Troubleshooting

### "No performance metrics shown"

1. Check that `perf_logger` is configured correctly
2. Verify `before_request` and `after_request` hooks are registered
3. Ensure you're not running in debug mode (Flask debug overrides middleware)

### "DB time is always 0"

Database query tracking requires the `track_db_time` decorator on database operations. Not all operations may be tracked yet.

### "Client metrics differ from server"

Client-side timing includes network latency. The formula is:
```
Client Time = Server Time + Network Time + Browser Processing
```

## Next Steps

1. **Run load test** - Use `ab` or `wrk` to simulate traffic
2. **Profile slow endpoints** - Use `cProfile` for detailed analysis
3. **Add caching layer** - Implement Redis for frequently accessed data
4. **Optimize database** - Add indexes, review query patterns
5. **Deploy with Gunicorn** - Replace Flask dev server with production WSGI

## Resources

- [Flask Performance Best Practices](https://flask.palletsprojects.com/en/2.3.x/tutorial/deploy/)
- [SQLAlchemy Performance](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [Web Performance Optimization](https://web.dev/performance/)
