# backend/routes_api_cricket.py

"""
WOVCC Flask Application - Cricket Data API Routes
Reads pre-scraped data from PostgreSQL database for high performance.
The scraper runs as a daemon service, updating the database periodically.
Falls back to scraped_data.json if database is empty (migration support).
"""

from flask import Blueprint, jsonify, request
import os
import json
from datetime import datetime
import logging
import shutil

# The scraper is now only used for its utility functions by other modules if needed,
# but not for live scraping within the API requests.
from scraper import scraper, scrape_to_database
from auth import require_admin

logger = logging.getLogger(__name__)
cricket_api_bp = Blueprint('cricket_api', __name__, url_prefix='/api')

# --- Helper Function to Load Scraped Data ---

# Define the path to the data file (fallback)
SCRAPED_DATA_PATH = os.path.join(os.path.dirname(__file__), 'scraped_data.json')

# In-memory cache for database data (refreshes every 60 seconds)
_db_cache = None
_db_cache_time = None
_DB_CACHE_TTL = 60  # seconds


def get_scraped_data():
    """
    Loads cricket data from database with in-memory caching.
    Falls back to JSON file if database is empty (for migration support).
    """
    global _db_cache, _db_cache_time
    
    import time
    now = time.time()
    
    # Return cached data if still fresh
    if _db_cache and _db_cache_time and (now - _db_cache_time) < _DB_CACHE_TTL:
        return _db_cache
    
    # Try to load from database
    try:
        from database import get_db, ScrapedData
        db = next(get_db())
        try:
            data_row = db.query(ScrapedData).filter(ScrapedData.id == 1).first()
            if data_row and data_row.teams_data:
                data = data_row.to_dict()
                _db_cache = data
                _db_cache_time = now
                logger.debug("Loaded scraped data from database")
                return data
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not load from database, falling back to JSON: {e}")
    
    # Fallback to JSON file
    try:
        file_mod_time = os.path.getmtime(SCRAPED_DATA_PATH)
        with open(SCRAPED_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _db_cache = data
            _db_cache_time = now
            logger.debug("Loaded scraped data from JSON file (fallback)")
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Could not load scraped data from any source: {e}")
        # Return a default empty structure to prevent crashes
        return {'teams': [], 'fixtures': [], 'results': [], 'last_updated': None}

# ----- Cricket Data API (Now reading from file) -----

@cricket_api_bp.route('/teams', methods=['GET'])
def get_teams():
    """Get list of all teams from the pre-scraped data file."""
    data = get_scraped_data()
    teams = data.get('teams', [])
    return jsonify({
        'success': True,
        'teams': teams,
        'count': len(teams)
    })

@cricket_api_bp.route('/fixtures', methods=['GET'])
def get_fixtures():
    """Get upcoming fixtures from the pre-scraped data file."""
    team_id = request.args.get('team', 'all')
    data = get_scraped_data()
    fixtures = data.get('fixtures', [])

    if team_id and team_id.lower() != 'all':
        fixtures = [f for f in fixtures if f.get('team_id') == str(team_id)]

    return jsonify({
        'success': True,
        'fixtures': fixtures,
        'count': len(fixtures)
    })

@cricket_api_bp.route('/results', methods=['GET'])
def get_results():
    """Get recent results from the pre-scraped data file."""
    team_id = request.args.get('team', 'all')
    limit = request.args.get('limit', 10, type=int)
    data = get_scraped_data()
    results = data.get('results', [])

    if team_id and team_id.lower() != 'all':
        results = [r for r in results if r.get('team_id') == str(team_id)]
    
    # The results in the file are already sorted, so we just limit them
    limited_results = results[:limit]

    return jsonify({
        'success': True,
        'results': limited_results,
        'count': len(limited_results)
    })

@cricket_api_bp.route('/data', methods=['GET'])
def get_all_data():
    """Get combined dataset from the pre-scraped data file."""
    team_id = request.args.get('team', 'all')
    limit = request.args.get('limit', 9999, type=int)
    data = get_scraped_data()
    
    fixtures = data.get('fixtures', [])
    results = data.get('results', [])

    if team_id and team_id.lower() != 'all':
        fixtures = [f for f in fixtures if f.get('team_id') == str(team_id)]
        results = [r for r in results if r.get('team_id') == str(team_id)]

    return jsonify({
        'success': True,
        'last_updated': data.get('last_updated'),
        'teams': data.get('teams', []),
        'fixtures': fixtures,
        'results': results[:limit]
    })

@cricket_api_bp.route('/match-status', methods=['GET'])
def match_status():
    """Check if there are matches scheduled for today from the pre-scraped data file."""
    data = get_scraped_data()
    fixtures = data.get('fixtures', [])
    today = datetime.now().strftime('%Y-%m-%d')
    has_matches = any(f.get('date_iso') == today for f in fixtures)
    
    return jsonify({
        'success': True,
        'has_matches_today': has_matches
    })

# ----- Admin and Utility Routes (Unchanged) -----

@cricket_api_bp.route('/live-config', methods=['GET'])
def get_live_config():
    """Get current live match configuration from database"""
    from database import get_db, LiveConfig
    try:
        db = next(get_db())
        try:
            config_row = db.query(LiveConfig).filter(LiveConfig.id == 1).first()
            if config_row:
                config = config_row.to_dict()
            else:
                config = {'is_live': False, 'livestream_url': '', 'selected_match': None}
            return jsonify({'success': True, 'config': config})
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting live config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cricket_api_bp.route('/live-config', methods=['POST'])
@require_admin
def update_live_config(user):
    """Update live match configuration in database (admin only)"""
    from database import get_db, LiveConfig
    import json as json_lib
    try:
        data = request.get_json()
        db = next(get_db())
        try:
            config_row = db.query(LiveConfig).filter(LiveConfig.id == 1).first()
            
            if not config_row:
                # Create new config row
                config_row = LiveConfig(id=1)
                db.add(config_row)
            
            # Update fields
            config_row.is_live = data.get('is_live', config_row.is_live if config_row.is_live is not None else False)
            config_row.livestream_url = data.get('livestream_url', config_row.livestream_url or '')
            
            if 'selected_match' in data:
                if data['selected_match']:
                    config_row.selected_match_data = json_lib.dumps(data['selected_match'])
                else:
                    config_row.selected_match_data = None
            
            config_row.last_updated = datetime.now()
            
            db.commit()
            
            config = config_row.to_dict()
            return jsonify({'success': True, 'message': 'Live configuration updated', 'config': config})
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error updating live config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@cricket_api_bp.route('/clear-cache', methods=['POST'])
@require_admin
def clear_cache(user):
    """
    Manual trigger to refresh scraped data.
    Runs the scraper and saves directly to database.
    """
    try:
        # Run the scraper and save to database
        success = scrape_to_database()
        
        # Clear the in-memory cache to force a reload
        global _db_cache, _db_cache_time
        _db_cache = None
        _db_cache_time = None
        
        # Clear the old file-based cache directory
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)

        if success:
            return jsonify({'success': True, 'message': 'Scraper data refreshed successfully'})
        else:
            return jsonify({'success': True, 'message': 'Scrape had errors but old data preserved (stale-while-revalidate)'})
    except Exception as e:
        logger.error(f"Error in clear-cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500