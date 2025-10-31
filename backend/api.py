"""
WOVCC API Server
Flask API for serving cricket data to the frontend
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from scraper import scraper
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'WOVCC API',
        'version': '1.0.0'
    })


@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Get list of all teams"""
    try:
        teams = scraper.get_teams()
        return jsonify({
            'success': True,
            'teams': teams,
            'count': len(teams)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/fixtures', methods=['GET'])
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
        return jsonify({
            'success': True,
            'fixtures': fixtures,
            'count': len(fixtures)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/results', methods=['GET'])
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
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data', methods=['GET'])
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

                return jsonify({
                    'success': True,
                    'last_updated': data.get('last_updated'),
                    'teams': data.get('teams', []),
                    'fixtures': fixtures,
                    'results': results
                })
            # If file not present, fall through to live scrape

        # Live scrape (default)
        teams = scraper.get_teams()
        fixtures = scraper.get_team_fixtures(team_id)
        results = scraper.get_team_results(team_id, limit)

        return jsonify({
            'success': True,
            'last_updated': datetime.now().isoformat(),
            'teams': teams,
            'fixtures': fixtures,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/match-status', methods=['GET'])
def match_status():
    """Check if there are matches scheduled for today"""
    try:
        has_matches = scraper.check_matches_today()
        return jsonify({
            'success': True,
            'has_matches_today': has_matches
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'has_matches_today': False
        }), 500


@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
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


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    print(f"Starting WOVCC API on port {PORT}...")
    print(f"Debug mode: {DEBUG}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

