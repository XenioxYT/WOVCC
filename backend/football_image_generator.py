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
    Create linear gradient background:
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


def generate_match_graphic(
    home_team: str,
    away_team: str,
    competition: str,
    match_date: str,
    match_time: str,
    output_path: str = None
) -> str:
    """
    Generate a TNT Sports-style match fixture graphic.
    
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
    BORDER_WIDTH = 20  # Pink border width
    
    # Colors
    WHITE = (255, 255, 255)
    LIGHT_GRAY = (180, 180, 195)
    PINK = (255, 0, 127)  # Vibrant Pink #FF007F for border/accents (TNT Style)
    GRADIENT_PINK = (130, 42, 146) # Underlying deep pink for gradient
    
    # Create gradient background
    img = create_gradient_background(WIDTH, HEIGHT)
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
    draw.text(((WIDTH - comp_width) // 2, comp_y), comp_text, fill=LIGHT_GRAY, font=font_competition)
    
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
                     fill=(60, 60, 80), outline=LIGHT_GRAY, width=2)
    
    if away_badge:
        away_badge_resized = away_badge.resize((badge_size, badge_size), Image.Resampling.LANCZOS)
        img.paste(away_badge_resized, (away_badge_x, badge_y), away_badge_resized)
    else:
        draw.ellipse([away_badge_x, badge_y, away_badge_x + badge_size, badge_y + badge_size],
                     fill=(60, 60, 80), outline=LIGHT_GRAY, width=2)
    
    # === HOME TEAM NAME (big, centered) ===
    home_y = badge_y + badge_size + 60
    home_text = home_team.upper()
    home_bbox = draw.textbbox((0, 0), home_text, font=font_team)
    home_width = home_bbox[2] - home_bbox[0]
    draw.text(((WIDTH - home_width) // 2, home_y), home_text, fill=WHITE, font=font_team)
    
    # === "v" ===
    vs_y = home_y + 100
    vs_text = "v"
    vs_bbox = draw.textbbox((0, 0), vs_text, font=font_vs)
    vs_width = vs_bbox[2] - vs_bbox[0]
    draw.text(((WIDTH - vs_width) // 2, vs_y), vs_text, fill=LIGHT_GRAY, font=font_vs)
    
    # === AWAY TEAM NAME (big, centered) ===
    away_y = vs_y + 70
    away_text = away_team.upper()
    away_bbox = draw.textbbox((0, 0), away_text, font=font_team)
    away_width = away_bbox[2] - away_bbox[0]
    draw.text(((WIDTH - away_width) // 2, away_y), away_text, fill=WHITE, font=font_team)
    
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
    
    # Brighter purple/pink
    BRIGHT_PURPLE = (220, 100, 255) 
    
    draw.text((date_x, datetime_y), date_text, fill=LIGHT_GRAY, font=font_date)
    draw.text((time_x, datetime_y), time_text, fill=BRIGHT_PURPLE, font=font_time)
    
    # === TNT SPORTS LOGO (bottom center) ===
    tnt_logo_path = os.path.join(ASSETS_DIR, 'TNT_sports.png')
    if os.path.exists(tnt_logo_path):
        tnt_logo = Image.open(tnt_logo_path).convert("RGBA")
        logo_height = 60
        aspect = tnt_logo.width / tnt_logo.height
        logo_width = int(logo_height * aspect)
        tnt_logo = tnt_logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        logo_x = (WIDTH - logo_width) // 2
        logo_y = HEIGHT - logo_height - 50
        img.paste(tnt_logo, (logo_x, logo_y), tnt_logo)
    
    # === SAVE IMAGE ===
    if not output_path:
        home_clean = sanitize_filename(home_team)
        away_clean = sanitize_filename(away_team)
        output_path = os.path.join(UPLOADS_DIR, f"football_{home_clean}_vs_{away_clean}.webp")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "WEBP", quality=92)
    logger.info(f"Generated match graphic: {output_path}")
    
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
