"""
WOVCC Flask Application - Cricket Data API Routes
Handles all endpoints related to Play-Cricket data and live config.
"""

from flask import Blueprint, jsonify, request
import os
import json
from datetime import datetime
import logging

from scraper import scraper
from auth import require_admin

logger = logging.getLogger(__name__)
cricket_api_bp = Blueprint('cricket_api', __name__, url_prefix='/api')

# ----- Cricket Data API -----

@cricket_api_bp.route('/teams', methods=['GET'])
def get_teams():
    """Get list of all teams"""
    try:
        teams = scraper.get_teams()
        
        resp = jsonify({
            'success': True,
            'teams': teams,
            'count': len(teams)
        })
        return resp
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cricket_api_bp.route('/fixtures', methods=['GET'])
def get_fixtures():
    """Get upcoming fixtures
    
    Query params:
        team: team_id (optional, default: all)
    """
    team_id = request.args.get('team', None)
    
    if team_id and team_id.lower() == 'all':
        team_id = None
    
    try:
        fixtures = scraper.get_team_fixtures(team_id)
        resp = jsonify({
            'success': True,
            'fixtures': fixtures,
            'count': len(fixtures)
        })
        return resp
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cricket_api_bp.route('/results', methods=['GET'])
def get_results():
    """Get recent results
    
    Query params:
        team: team_id (optional, default: all)
        limit: number of results (optional, default: 10)
    """
    team_id = request.args.get('team', None)
    limit = request.args.get('limit', 10, type=int)
    
    if team_id and team_id.lower() == 'all':
        team_id = None
    
    try:
        results = scraper.get_team_results(team_id, limit)
        resp = jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        return resp
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cricket_api_bp.route('/data', methods=['GET'])
def get_all_data():
    """Get combined dataset (teams, fixtures, results) in one call.

    Query params:
        team: team_id (optional, default: all)
        limit: number of results (optional, default: 9999)
        source: 'live' (default) or 'file' to read existing scraped_data.json
    """
    team_id = request.args.get('team', None)
    limit = request.args.get('limit', 9999, type=int)
    source = request.args.get('source', 'live').lower()

    if team_id and team_id.lower() == 'all':
        team_id = None

    try:
        if source == 'file':
            # Serve directly from saved JSON if available
            file_path = os.path.join(os.path.dirname(__file__), 'scraped_data.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Optionally filter fixtures/results by team and apply limit
                fixtures = data.get('fixtures', [])
                results = data.get('results', [])
                if team_id:
                    fixtures = [fx for fx in fixtures if fx.get('team_id') == str(team_id)]
                    results = [rs for rs in results if rs.get('team_id') == str(team_id)]
                if isinstance(limit, int) and limit > 0:
                    results = results[:limit]

                resp = jsonify({
                    'success': True,
                    'last_updated': data.get('last_updated'),
                    'teams': data.get('teams', []),
                    'fixtures': fixtures,
                    'results': results
                })
                return resp
            # If file not present, fall through to live scrape

        # Live scrape (default)
        teams = scraper.get_teams()
        fixtures = scraper.get_team_fixtures(team_id)
        results = scraper.get_team_results(team_id, limit)

        resp = jsonify({
            'success': True,
            'last_updated': datetime.now().isoformat(),
            'teams': teams,
            'fixtures': fixtures,
            'results': results
        })
        return resp
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cricket_api_bp.route('/match-status', methods=['GET'])
def match_status():
    """Check if there are matches scheduled for today"""
    try:
        has_matches = scraper.check_matches_today()
        resp = jsonify({
            'success': True,
            'has_matches_today': has_matches
        })
        return resp
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'has_matches_today': False
        }), 500


@cricket_api_bp.route('/live-config', methods=['GET'])
def get_live_config():
    """Get current live match configuration"""
    try:
        config_file = os.path.join(os.path.dirname(__file__), 'live_config.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # Default config
            config = {
                'is_live': False,
                'livestream_url': '',
                'selected_match': None
            }
        
        resp = jsonify({
            'success': True,
            'config': config
        })
        return resp
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cricket_api_bp.route('/live-config', methods=['POST'])
@require_admin
def update_live_config(user):
    """Update live match configuration (admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Load existing config or create new one
        config_file = os.path.join(os.path.dirname(__file__), 'live_config.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                'is_live': False,
                'livestream_url': '',
                'selected_match': None
            }
        
        # Update config with provided data
        if 'is_live' in data:
            config['is_live'] = data['is_live']
        
        if 'livestream_url' in data:
            config['livestream_url'] = data['livestream_url']
        
        if 'selected_match' in data:
            config['selected_match'] = data['selected_match']
        
        # Add last updated timestamp
        config['last_updated'] = datetime.now().isoformat()
        
        # Save config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Live configuration updated successfully',
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cricket_api_bp.route('/clear-cache', methods=['POST'])
@require_admin
def clear_cache(user):
    """Clear all cached data (admin endpoint)"""
    try:
        import shutil
        cache_dir = 'cache'
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cricket_api_bp.route('/performance/stats')
@require_admin
def performance_stats(user):
    """Get performance statistics (admin only)"""
    return jsonify({
        'success': True,
        'message': 'Check server logs for detailed performance metrics',
        'note': 'Performance data is logged for each request with timing breakdowns',
        'headers_info': {
            'X-Response-Time': 'Total response time in milliseconds',
            'X-DB-Queries': 'Number of database queries executed',
            'X-DB-Time': 'Total database query time in milliseconds'
        }
    })