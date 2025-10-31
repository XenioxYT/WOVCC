"""
WOVCC Play-Cricket Web Scraper
Scrapes fixture and result data from Play-Cricket pages

Can be imported as a module or run standalone to generate
a 'scraped_data.json' file.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os
import time
from typing import List, Dict, Optional, Any

CLUB_ID = 6908
BASE_URL = "https://wov.play-cricket.com"
CACHE_DIR = "cache"

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)


class PlayCricketScraper:
    """Scraper for WOVCC Play-Cricket pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Runtime controls
        self.disable_cache: bool = True
        self.request_delay_seconds: float = 0.0
        self.request_timeout_seconds: int = 15
        self.verbose: bool = False
        # Diagnostics
        self.last_cache_hit: bool = False
        self.last_cache_hit_key: Optional[str] = None

    def _request_get(self, url: str) -> requests.Response:
        """Centralized GET that honors delay and timeout"""
        if self.request_delay_seconds and self.request_delay_seconds > 0:
            time.sleep(self.request_delay_seconds)
        return self.session.get(url, timeout=self.request_timeout_seconds)
    
    def _get_cache_path(self, key: str) -> str:
        """Get cache file path for a given key"""
        return os.path.join(CACHE_DIR, f"{key}.json")
    
    def _read_cache(self, key: str, max_age_hours: int = 6) -> Optional[Any]:
        """Read from cache if exists and not expired"""
        cache_path = self._get_cache_path(key)
        
        if self.disable_cache:
            self.last_cache_hit = False
            self.last_cache_hit_key = key
            return None
        
        if not os.path.exists(cache_path):
            self.last_cache_hit = False
            self.last_cache_hit_key = key
            return None
        
        # Check cache age
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - cache_time > timedelta(hours=max_age_hours):
            self.last_cache_hit = False
            self.last_cache_hit_key = key
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.last_cache_hit = True
                self.last_cache_hit_key = key
                return data
        except Exception:
            self.last_cache_hit = False
            self.last_cache_hit_key = key
            return None
    
    def _write_cache(self, key: str, data: Any):
        """Write data to cache"""
        cache_path = self._get_cache_path(key)
        if self.disable_cache:
            return
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing cache for {key}: {e}")
            
    def _parse_match_date(self, date_str: str) -> Optional[str]:
        """Parses 'Sunday 09 November 2025' to '2025-11-09'"""
        try:
            # Format from HTML: '%A %d %B %Y'
            dt = datetime.strptime(date_str, '%A %d %B %Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            print(f"Could not parse date: {date_str}")
            return None

    def get_teams(self) -> List[Dict]:
        """Get list of all teams"""
        cache_key = "teams"
        cached = self._read_cache(cache_key, max_age_hours=24)
        if cached:
            return cached
        
        url = f"{BASE_URL}/Teams"
        response = self._request_get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        teams = []
        seen_ids = set()
        
        # Find all team "boxes" which contain the name
        for box in soup.find_all('div', class_='box-fame'):
            team_name_tag = box.find('h3')
            if not team_name_tag:
                continue
            
            team_name = team_name_tag.get_text(strip=True)
            
            # The link is a sibling of the box, in the parent container
            # We search the parent `div` for the link
            container = box.find_parent('div', class_='col-md-4')
            if not container:
                # Fallback if structure is different
                container = box.find_parent()

            if not container:
                continue

            team_link_tag = container.find('a', class_='link-view-famedetails')
            if not team_link_tag:
                 team_link_tag = container.find('a', class_='link-view-famedetails2')

            if team_link_tag and team_link_tag.get('href'):
                href = team_link_tag['href']
                
                if '/Teams/' in href:
                    try:
                        team_id = href.split('/')[-1]
                        if team_id.isdigit() and team_id not in seen_ids:
                            seen_ids.add(team_id)
                            teams.append({
                                'id': team_id,
                                'name': team_name,
                                'url': f"{BASE_URL}{href}"
                            })
                    except Exception:
                        continue # Skip malformed links
        
        self._write_cache(cache_key, teams)
        return teams
    
    def get_team_fixtures(self, team_id: str = None) -> List[Dict]:
        """Get upcoming fixtures for a team or all teams"""
        cache_key = f"fixtures_{team_id or 'all'}"
        cached = self._read_cache(cache_key, max_age_hours=6)
        if cached:
            return cached
        
        all_fixtures = []
        
        if team_id:
            teams_to_scrape = [{'id': team_id}]
        else:
            teams_to_scrape = self.get_teams()
        
        for team in teams_to_scrape:
            url = f"{BASE_URL}/Teams/{team['id']}"
            try:
                response = self._request_get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get team name from the page H3 for context
                team_name_tag = soup.select_one('div.titleinfo-team-right h3')
                team_name = team_name_tag.get_text(strip=True) if team_name_tag else f"Team {team['id']}"
                
                # Find the fixtures section
                fixtures_section = soup.find('div', class_='section-fixtures')
                if not fixtures_section:
                    continue # No fixtures section at all
                
                # Check for "NO FIXTURES" message
                if fixtures_section.find('div', class_='no-results'):
                    continue # Team has no fixtures

                current_date_str = ""
                current_date_iso = ""

                # Iterate over all ROWS within the section
                for row in fixtures_section.find_all('div', class_='row'):
                    # Check if this row is a date header
                    date_header = row.find('div', class_='title2')
                    if date_header:
                        current_date_str = date_header.get_text(strip=True)
                        current_date_iso = self._parse_match_date(current_date_str)
                        continue
                    
                    # Check if this row contains a match card
                    card = row.find('div', class_='card-table')
                    if card:
                        home_team_tag = card.select_one('td.text-md-right p.txt1')
                        away_team_tag = card.select_one('td.text-md-left p.txt1')
                        time_tag = card.find('p', class_='time')
                        location_tag = card.find('p', class_='location')
                        link_tag = card.find('a', class_='link-scorecard')

                        if not (home_team_tag and away_team_tag):
                            continue

                        fixture_data = {
                            'team_name_scraping': team_name, # The team page we are on
                            'team_id': team['id'],
                            'date_str': current_date_str,
                            'date_iso': current_date_iso,
                            'home_team': home_team_tag.get_text(strip=True),
                            'away_team': away_team_tag.get_text(strip=True),
                            'time': time_tag.get_text(strip=True) if time_tag else None,
                            'location': location_tag.get_text(strip=True) if location_tag else None,
                            'match_url': f"{BASE_URL}{link_tag['href']}" if link_tag and link_tag.get('href') else None
                        }
                        all_fixtures.append(fixture_data)
                        
            except Exception as e:
                print(f"Error fetching fixtures for team {team['id']}: {e}")
                continue
        
        # De-duplicate fixtures if scraping 'all'
        final_fixtures = []
        seen_urls = set()
        if not team_id:
            for fix in all_fixtures:
                url = fix.get('match_url')
                if url and url not in seen_urls:
                    final_fixtures.append(fix)
                    seen_urls.add(url)
        else:
            final_fixtures = all_fixtures

        self._write_cache(cache_key, final_fixtures)
        return final_fixtures
    
    def get_team_results(self, team_id: str = None, limit: int = 10) -> List[Dict]:
        """Get recent results for a team or all teams"""
        cache_key = f"results_{team_id or 'all'}_{limit}"
        cached = self._read_cache(cache_key, max_age_hours=6)
        if cached:
            return cached[:limit] # Apply limit to cached data
        
        all_results = []
        
        if team_id:
            teams_to_scrape = [{'id': team_id}]
        else:
            teams_to_scrape = self.get_teams()

        for team in teams_to_scrape:
            url = f"{BASE_URL}/Teams/{team['id']}"
            try:
                response = self._request_get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                team_name_tag = soup.select_one('div.titleinfo-team-right h3')
                team_name = team_name_tag.get_text(strip=True) if team_name_tag else f"Team {team['id']}"
                
                results_section = soup.find('div', class_='section-results')
                if not results_section:
                    continue
                
                if results_section.find('div', class_='no-results'):
                    continue # No results for this team

                current_date_str = ""
                current_date_iso = ""

                # Iterate over all ROWS within the section
                for row in results_section.find_all('div', class_='row'):
                    # Check if this row is a date header
                    date_header = row.find('div', class_='title2')
                    if date_header:
                        current_date_str = date_header.get_text(strip=True)
                        current_date_iso = self._parse_match_date(current_date_str)
                        continue

                    # Check if this row contains a match card
                    card = row.find('div', class_='card-table')
                    if card:
                        home_team_tag = card.select_one('td.text-md-right p.txt1')
                        away_team_tag = card.select_one('td.text-md-left p.txt1')
                        home_score_tag = card.select_one('td.text-md-right p.txt2')
                        away_score_tag = card.select_one('td.text-md-left p.txt2')
                        
                        # Get desktop or mobile summary
                        summary_tag = card.select_one('div.match-status div.fonts-gt') 
                        if not summary_tag:
                            summary_tag = card.select_one('div.match-status-mobile')
                        
                        link_tag = card.find('a', class_='link-scorecard')

                        if not (home_team_tag and away_team_tag):
                            continue
                        
                        # Extract only the main text, ignoring child tags like the icon
                        if summary_tag:
                            summary_text = summary_tag.find(string=True, recursive=False)
                            summary_text = summary_text.strip() if summary_text else ""
                        else:
                            summary_text = ""
                            
                        summary_upper = summary_text.upper()
                        
                        # Check win/loss based on our club name
                        is_win = False
                        is_loss = False
                        
                        if "WICKERSLEY OLD VILLAGE CC" in summary_upper:
                            # Our club name is mentioned in the summary
                            if 'WON' in summary_upper:
                                is_win = True
                            elif 'LOST' in summary_upper:
                                is_loss = True
                        elif 'WON' in summary_upper or 'LOST' in summary_upper:
                            # Summary mentions win/loss but not our club name
                            # This means the opponent won or lost
                            if 'WON' in summary_upper:
                                # Opponent won, so we lost
                                is_loss = True
                            elif 'LOST' in summary_upper:
                                # Opponent lost, so we won
                                is_win = True
                        
                        result_data = {
                            'team_name_scraping': team_name,
                            'team_id': team['id'],
                            'date_str': current_date_str,
                            'date_iso': current_date_iso,
                            'home_team': home_team_tag.get_text(strip=True),
                            'away_team': away_team_tag.get_text(strip=True),
                            'home_score': home_score_tag.get_text(separator=' ', strip=True) if home_score_tag else None,
                            'away_score': away_score_tag.get_text(separator=' ', strip=True) if away_score_tag else None,
                            'summary': summary_text,
                            'is_win': is_win,
                            'is_loss': is_loss,
                            'match_url': f"{BASE_URL}{link_tag['href']}" if link_tag and link_tag.get('href') else None
                        }
                        all_results.append(result_data)
                        
            except Exception as e:
                print(f"Error fetching results for team {team['id']}: {e}")
                continue

        # De-duplicate results if scraping 'all'
        final_results = []
        seen_urls = set()
        if not team_id:
            for res in all_results:
                url = res.get('match_url')
                if url and url not in seen_urls:
                    final_results.append(res)
                    seen_urls.add(url)
        else:
            final_results = all_results
        
        # Sort by date (descending) before caching
        final_results.sort(key=lambda x: x.get('date_iso') or '0000-00-00', reverse=True)
        
        self._write_cache(cache_key, final_results)
        return final_results[:limit]
    
    def check_matches_today(self) -> bool:
        """Check if there are any matches scheduled for today"""
        try:
            # Get fixtures for ALL teams
            fixtures = self.get_team_fixtures() # Uses caching
            today = datetime.now().strftime('%Y-%m-%d')
            
            for fixture in fixtures:
                if fixture.get('date_iso') == today:
                    return True
        except Exception as e:
            print(f"Error in check_matches_today: {e}")
            return False # Fail safe
        
        return False


# Singleton instance
scraper = PlayCricketScraper()

# --- Standalone execution ---

if __name__ == "__main__":
    """
    This block runs when the script is executed directly
    (e.g., python scraper.py)
    It fetches all data and saves it to a single JSON file.
    """
    
    print("--- Running WOVCC Scraper in Standalone Mode ---")
    
    # Default runtime configuration (no CLI args)
    # Caching is disabled by default; adjust attributes below if needed.

    all_data = {
        'last_updated': datetime.now().isoformat()
    }
    
    # 1. Fetch all teams
    print("Fetching all teams...")
    try:
        _t0 = time.perf_counter()
        teams_data = scraper.get_teams()
        _dt = time.perf_counter() - _t0
        all_data['teams'] = teams_data
        cache_note = " (from cache)" if scraper.last_cache_hit else ""
        print(f"Successfully found {len(teams_data)} teams{cache_note} in {_dt:.2f}s.")
    except Exception as e:
        print(f"Error fetching teams: {e}")
        all_data['teams'] = []

    # 2. Fetch all fixtures
    print("Fetching all fixtures...")
    try:
        # Pass team_id=None to get all fixtures
        _t0 = time.perf_counter()
        fixtures_data = scraper.get_team_fixtures(team_id=None)
        _dt = time.perf_counter() - _t0
        all_data['fixtures'] = fixtures_data
        cache_note = " (from cache)" if scraper.last_cache_hit else ""
        print(f"Successfully found {len(fixtures_data)} upcoming fixtures{cache_note} in {_dt:.2f}s.")
    except Exception as e:
        print(f"Error fetching fixtures: {e}")
        all_data['fixtures'] = []

    # 3. Fetch all results
    print("Fetching all results...")
    try:
        # Pass team_id=None and a high limit to get all results
        _t0 = time.perf_counter()
        results_data = scraper.get_team_results(team_id=None, limit=9999)
        _dt = time.perf_counter() - _t0
        all_data['results'] = results_data
        cache_note = " (from cache)" if scraper.last_cache_hit else ""
        print(f"Successfully found {len(results_data)} recent results{cache_note} in {_dt:.2f}s.")
    except Exception as e:
        print(f"Error fetching results: {e}")
        all_data['results'] = []

    # 4. Save all data to a file
    output_filename = "scraped_data.json"
    print(f"\nSaving all data to {output_filename}...")
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=4)
        print("--- Scrape complete. Data saved. ---")
    except Exception as e:
        print(f"Fatal error saving data to JSON: {e}")

