"""
Football Match Image Generator
Generates TNT Sports-style fixture graphics for football matches

Design based on TNT Sports broadcast graphics:
- Stacked vertical layout with big bold team names
- Gradient background (pink bottom-right to dark navy)
- Clean minimal aesthetic
"""

import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import logging
import math

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, '..', 'assets')
CACHE_DIR = os.path.join(BASE_DIR, 'cache', 'team_logos')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')

# Ensure directories exist
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# TheSportsDB API (V1 - Free tier)
SPORTSDB_API_BASE = "https://www.thesportsdb.com/api/v1/json/3"

# Font paths - DejaVu for Docker, Inter as fallback for local dev
FONT_PATHS = {
    # Try Inter first (local dev), then DejaVu (Docker)
    'bold': [
        '/usr/share/fonts/opentype/inter/Inter-Bold.otf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ],
    'extrabold': [
        '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ],
    'semibold': [
        '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ],
    'medium': [
        '/usr/share/fonts/opentype/inter/Inter-Medium.otf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ],
}


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for use in filenames.
    Replaces problematic characters (slashes, colons, etc.) with underscores.
    """
    # Characters that are problematic in filenames
    # Forward slash, backslash, colon, asterisk, question mark, quotes, etc.
    problematic_chars = ['/', '\\', ':', '*', '?', '"', "'", '<', '>', '|']
    
    result = name.lower()
    for char in problematic_chars:
        result = result.replace(char, '_')
    
    # Replace spaces with underscores
    result = result.replace(' ', '_')
    
    # Remove any double underscores that may have been created
    while '__' in result:
        result = result.replace('__', '_')
    
    # Strip leading/trailing underscores
    result = result.strip('_')
    
    return result


def get_font(style: str, size: int) -> ImageFont.FreeTypeFont:
    """Get a font with fallback to default."""
    paths = FONT_PATHS.get(style, FONT_PATHS['bold'])
    
    for path in paths:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception as e:
            logger.warning(f"Could not load font {path}: {e}")
            continue
    
    # Final fallback to PIL default
    return ImageFont.load_default()


def fetch_team_badge(team_name: str, sport: str = "Soccer") -> Image.Image | None:
    """Fetch team badge from TheSportsDB API with caching."""
    cache_filename = sanitize_filename(team_name) + ".png"
    cache_path = os.path.join(CACHE_DIR, cache_filename)
    
    if os.path.exists(cache_path):
        logger.info(f"Using cached logo for {team_name}")
        return Image.open(cache_path).convert("RGBA")
    
    try:
        url = f"{SPORTSDB_API_BASE}/searchteams.php?t={team_name}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("teams"):
            logger.warning(f"No team found for: {team_name}")
            return None
        
        # Find soccer team
        team = None
        for t in data["teams"]:
            if t.get("strSport", "").lower() == sport.lower():
                team = t
                logger.info(f"Found {sport} team: {t.get('strTeam')}")
                break
        
        if not team:
            team = data["teams"][0]
        
        badge_url = team.get("strBadge") or team.get("strLogo")
        if not badge_url:
            return None
        
        logger.info(f"Fetching badge for {team_name}")
        badge_response = requests.get(badge_url, timeout=10)
        badge_response.raise_for_status()
        
        badge_image = Image.open(BytesIO(badge_response.content)).convert("RGBA")
        badge_image.save(cache_path, "PNG")
        
        return badge_image
        
    except Exception as e:
        logger.error(f"Error fetching badge for {team_name}: {e}")
        return None


def create_gradient_background(width: int, height: int) -> Image.Image:
    """
    Create TNT Sports linear gradient background:
    - Pink (130, 42, 146) concentrated in bottom-right corner only
    - Dark navy (20, 29, 40) everywhere else
    """
    # Colors as specified
    PINK = (130, 42, 146)
    DARK = (20, 29, 40)
    
    img = Image.new('RGB', (width, height), DARK)
    
    # Create gradient concentrated in bottom-right corner
    for y in range(height):
        for x in range(width):
            # Distance from bottom-right corner (normalized 0-1)
            # Higher values = closer to bottom-right
            t = (x / width + y / height) / 2
            
            # Apply strong curve to concentrate pink in corner only
            # This makes most of the image stay dark
            t = max(0, (t - 0.4) / 0.6)  # Only start gradient at 40% mark
            t = t ** 2.5  # Strong curve for tight corner concentration
            
            r = int(DARK[0] + (PINK[0] - DARK[0]) * t)
            g = int(DARK[1] + (PINK[1] - DARK[1]) * t)
            b = int(DARK[2] + (PINK[2] - DARK[2]) * t)
            
            img.putpixel((x, y), (r, g, b))
    
    return img


def create_sky_sports_background(width: int, height: int) -> Image.Image:
    """
    Create Sky Sports style background:
    - Clean white/light gray with subtle blue tint
    """
    # Light background with very subtle blue gradient
    LIGHT = (255, 255, 255)
    LIGHT_BLUE = (240, 244, 248)
    
    img = Image.new('RGB', (width, height), LIGHT)
    
    # Create a very subtle gradient from white to light blue
    for y in range(height):
        for x in range(width):
            t = (y / height) * 0.3  # Very subtle gradient
            
            r = int(LIGHT[0] + (LIGHT_BLUE[0] - LIGHT[0]) * t)
            g = int(LIGHT[1] + (LIGHT_BLUE[1] - LIGHT[1]) * t)
            b = int(LIGHT[2] + (LIGHT_BLUE[2] - LIGHT[2]) * t)
            
            img.putpixel((x, y), (r, g, b))
    
    return img


def generate_match_graphic(
    home_team: str,
    away_team: str,
    competition: str,
    match_date: str,
    match_time: str,
    output_path: str = None,
    broadcaster: str = 'tnt'
) -> str:
    """
    Generate a match fixture graphic in either TNT Sports or Sky Sports style.
    
    Args:
        broadcaster: 'tnt' for TNT Sports style, 'sky_sports' for Sky Sports style
    
    Layout:
    - Competition name at top
    - Two team badges side by side
    - HOME TEAM (big bold)
    - v
    - AWAY TEAM (big bold)
    - Date and Time at bottom
    """
    # Image dimensions - 2:1 Aspect Ratio (Wider)
    WIDTH = 1920
    HEIGHT = 960
    
    # Determine style based on broadcaster
    is_sky_sports = broadcaster.lower() == 'sky_sports'
    
    if is_sky_sports:
        # Sky Sports colors: White background, blue text, red accents
        PRIMARY_TEXT = (12, 61, 122)  # Sky Sports Blue #0c3d7a
        SECONDARY_TEXT = (100, 115, 140)  # Muted blue-gray
        ACCENT_COLOR = (196, 30, 58)  # Sky Sports Red #c41e3a
        TIME_COLOR = ACCENT_COLOR
        TEAM_TEXT = PRIMARY_TEXT
        VS_COLOR = SECONDARY_TEXT
        COMP_COLOR = SECONDARY_TEXT
        PLACEHOLDER_FILL = (220, 225, 230)
        PLACEHOLDER_OUTLINE = SECONDARY_TEXT
        
        # Create Sky Sports background
        img = create_sky_sports_background(WIDTH, HEIGHT)
        logo_filename = 'sky_sports_logo.png'
    else:
        # TNT Sports colors: Purple gradient, white text, pink accents
        PRIMARY_TEXT = (255, 255, 255)  # White
        SECONDARY_TEXT = (180, 180, 195)  # Light gray
        ACCENT_COLOR = (255, 0, 127)  # Vibrant Pink
        TIME_COLOR = (220, 100, 255)  # Bright purple/pink
        TEAM_TEXT = PRIMARY_TEXT
        VS_COLOR = SECONDARY_TEXT
        COMP_COLOR = SECONDARY_TEXT
        PLACEHOLDER_FILL = (60, 60, 80)
        PLACEHOLDER_OUTLINE = SECONDARY_TEXT
        
        # Create TNT Sports gradient background
        img = create_gradient_background(WIDTH, HEIGHT)
        logo_filename = 'TNT_sports.png'
    
    draw = ImageDraw.Draw(img)
    
    # Load fonts - sizes optimized for 1920x960
    font_competition = get_font('semibold', 52)
    font_team = get_font('extrabold', 90)  # Slightly smaller to ensure fit
    font_vs = get_font('medium', 42)
    # Fonts - SAME SIZE for alignment
    font_date = get_font('extrabold', 60)
    font_time = get_font('extrabold', 60)
    
    center_x = WIDTH // 2
    
    # === COMPETITION NAME (top) ===
    comp_y = 60
    comp_text = competition.upper()
    comp_bbox = draw.textbbox((0, 0), comp_text, font=font_competition)
    comp_width = comp_bbox[2] - comp_bbox[0]
    draw.text(((WIDTH - comp_width) // 2, comp_y), comp_text, fill=COMP_COLOR, font=font_competition)
    
    # === TEAM BADGES (side by side) ===
    home_badge = fetch_team_badge(home_team)
    away_badge = fetch_team_badge(away_team)
    
    badge_size = 180 # Slightly smaller
    badge_y = 140
    badge_spacing = 60  # Space between badges
    
    # Calculate positions for centered pair
    total_badges_width = badge_size * 2 + badge_spacing
    home_badge_x = center_x - total_badges_width // 2
    away_badge_x = home_badge_x + badge_size + badge_spacing
    
    if home_badge:
        home_badge_resized = home_badge.resize((badge_size, badge_size), Image.Resampling.LANCZOS)
        img.paste(home_badge_resized, (home_badge_x, badge_y), home_badge_resized)
    else:
        draw.ellipse([home_badge_x, badge_y, home_badge_x + badge_size, badge_y + badge_size], 
                     fill=PLACEHOLDER_FILL, outline=PLACEHOLDER_OUTLINE, width=2)
    
    if away_badge:
        away_badge_resized = away_badge.resize((badge_size, badge_size), Image.Resampling.LANCZOS)
        img.paste(away_badge_resized, (away_badge_x, badge_y), away_badge_resized)
    else:
        draw.ellipse([away_badge_x, badge_y, away_badge_x + badge_size, badge_y + badge_size],
                     fill=PLACEHOLDER_FILL, outline=PLACEHOLDER_OUTLINE, width=2)
    
    # === HOME TEAM NAME (big, centered) ===
    home_y = badge_y + badge_size + 60
    home_text = home_team.upper()
    home_bbox = draw.textbbox((0, 0), home_text, font=font_team)
    home_width = home_bbox[2] - home_bbox[0]
    draw.text(((WIDTH - home_width) // 2, home_y), home_text, fill=TEAM_TEXT, font=font_team)
    
    # === "v" ===
    vs_y = home_y + 100
    vs_text = "v"
    vs_bbox = draw.textbbox((0, 0), vs_text, font=font_vs)
    vs_width = vs_bbox[2] - vs_bbox[0]
    draw.text(((WIDTH - vs_width) // 2, vs_y), vs_text, fill=VS_COLOR, font=font_vs)
    
    # === AWAY TEAM NAME (big, centered) ===
    away_y = vs_y + 70
    away_text = away_team.upper()
    away_bbox = draw.textbbox((0, 0), away_text, font=font_team)
    away_width = away_bbox[2] - away_bbox[0]
    draw.text(((WIDTH - away_width) // 2, away_y), away_text, fill=TEAM_TEXT, font=font_team)
    
    # === DATE AND TIME (bottom) ===
    datetime_y = away_y + 130
    
    date_text = match_date.upper()
    time_text = match_time.upper()
    
    # Calculate widths
    date_bbox = draw.textbbox((0, 0), date_text, font=font_date)
    time_bbox = draw.textbbox((0, 0), time_text, font=font_time)
    
    date_width = date_bbox[2] - date_bbox[0]
    time_width = time_bbox[2] - time_bbox[0]
    
    # Center the entire "DATE [Space] TIME" block
    spacing = 30
    total_width = date_width + spacing + time_width
    
    date_x = (WIDTH - total_width) // 2
    time_x = date_x + date_width + spacing
    
    draw.text((date_x, datetime_y), date_text, fill=SECONDARY_TEXT, font=font_date)
    draw.text((time_x, datetime_y), time_text, fill=TIME_COLOR, font=font_time)
    
    # === BROADCASTER LOGO (bottom center) ===
    logo_path = os.path.join(ASSETS_DIR, logo_filename)
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo_height = 60
        aspect = logo.width / logo.height
        logo_width = int(logo_height * aspect)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        logo_x = (WIDTH - logo_width) // 2
        logo_y = HEIGHT - logo_height - 50
        img.paste(logo, (logo_x, logo_y), logo)
    
    # === SAVE IMAGE ===
    if not output_path:
        home_clean = sanitize_filename(home_team)
        away_clean = sanitize_filename(away_team)
        broadcaster_suffix = '_sky' if is_sky_sports else ''
        output_path = os.path.join(UPLOADS_DIR, f"football_{home_clean}_vs_{away_clean}{broadcaster_suffix}.webp")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "WEBP", quality=92)
    logger.info(f"Generated {broadcaster} match graphic: {output_path}")
    
    return output_path


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("⚽ Football Match Image Generator Test")
    print("=" * 50)
    
    # Test: Newcastle United vs Arsenal, FA Cup  
    output = generate_match_graphic(
        home_team="Newcastle United",
        away_team="Arsenal", 
        competition="FA Cup",
        match_date="SAT 14 JAN",
        match_time="2:30PM"
    )
    
    print(f"\n✅ Image generated: {output}")
