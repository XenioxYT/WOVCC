# backend/routes_api_cricket.py

"""
WOVCC Flask Application - Cricket Data API Routes
Reads pre-scraped data from scraped_data.json for high performance.
The scraper is run periodically by a background job.
"""

from flask import Blueprint, jsonify, request
import os
import json
from datetime import datetime
import logging
import shutil

# The scraper is now only used for its utility functions by other modules if needed,
# but not for live scraping within the API requests.
from scraper import scraper
from auth import require_admin

logger = logging.getLogger(__name__)
cricket_api_bp = Blueprint('cricket_api', __name__, url_prefix='/api')

# --- Helper Function to Load Scraped Data ---

# Define the path to the data file
SCRAPED_DATA_PATH = os.path.join(os.path.dirname(__file__), 'scraped_data.json')
_scraped_data_cache = None
_cache_load_time = None

def get_scraped_data():
    """
    Loads cricket data from scraped_data.json with in-memory caching.
    This avoids reading the file from disk on every single request.
    """
    global _scraped_data_cache, _cache_load_time

    try:
        # Check if the file has been modified since last cache read
        file_mod_time = os.path.getmtime(SCRAPED_DATA_PATH)
        if _scraped_data_cache and _cache_load_time and _cache_load_time >= file_mod_time:
            return _scraped_data_cache

        # File is new or has been updated, so re-read it
        with open(SCRAPED_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _scraped_data_cache = data
            _cache_load_time = file_mod_time
            return data
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Could not load or parse scraped_data.json: {e}")
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
    """Get current live match configuration"""
    try:
        config_file = os.path.join(os.path.dirname(__file__), 'live_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {'is_live': False, 'livestream_url': '', 'selected_match': None}
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@cricket_api_bp.route('/live-config', methods=['POST'])
@require_admin
def update_live_config(user):
    """Update live match configuration (admin only)"""
    try:
        data = request.get_json()
        config_file = os.path.join(os.path.dirname(__file__), 'live_config.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        config['is_live'] = data.get('is_live', config.get('is_live', False))
        config['livestream_url'] = data.get('livestream_url', config.get('livestream_url', ''))
        config['selected_match'] = data.get('selected_match', config.get('selected_match', None))
        config['last_updated'] = datetime.now().isoformat()

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            
        return jsonify({'success': True, 'message': 'Live configuration updated', 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@cricket_api_bp.route('/clear-cache', methods=['POST'])
@require_admin
def clear_cache(user):
    """
    This now serves as a manual trigger for the scraper.
    It runs the scraper script and clears the old scraper cache directory.
    """
    try:
        # Manually run the scraper script
        os.system('python backend/scraper.py')
        
        # Clear the old cache directory which is no longer used by the API
        cache_dir = 'cache'
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        # Clear the in-memory cache to force a reload from the new JSON file
        global _scraped_data_cache, _cache_load_time
        _scraped_data_cache = None
        _cache_load_time = None

        return jsonify({'success': True, 'message': 'Scraper data refreshed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500