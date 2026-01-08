"""
WOVCC Slug Utilities
Generates SEO-friendly URL slugs for events and other content.
"""

import re
import unicodedata
from datetime import datetime


def generate_slug(title: str, date: datetime = None, suffix: str = None) -> str:
    """
    Generate a URL-friendly slug from a title.
    
    Args:
        title: The title to convert to a slug
        date: Optional date to append (helps ensure uniqueness)
        suffix: Optional suffix (e.g., event ID for guaranteed uniqueness)
    
    Returns:
        A lowercase, hyphenated slug suitable for URLs
    
    Examples:
        "Christmas Party 2024" -> "christmas-party-2024"
        "New Year's Eve Bash!" -> "new-years-eve-bash"
        "Quiz Night" with date -> "quiz-night-jan-2025"
    """
    if not title:
        return None
    
    # Normalize unicode characters (e.g., é -> e)
    slug = unicodedata.normalize('NFKD', title)
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    
    # Convert to lowercase
    slug = slug.lower()
    
    # Replace common special characters
    slug = slug.replace('&', 'and')
    slug = slug.replace("'", '')
    slug = slug.replace('"', '')
    
    # Replace any non-alphanumeric characters with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading/trailing hyphens and collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    
    # Append date if provided (for uniqueness)
    if date:
        # Format: event-title-2025-01-07 (full date for recurring event uniqueness)
        date_suffix = date.strftime('%Y-%m-%d')
        slug = f"{slug}-{date_suffix}"
    
    # Append custom suffix if provided
    if suffix:
        slug = f"{slug}-{suffix}"
    
    # Limit length to avoid overly long URLs (max 200 chars)
    if len(slug) > 200:
        slug = slug[:200].rsplit('-', 1)[0]  # Cut at last hyphen to avoid partial words
    
    return slug


def ensure_unique_slug(base_slug: str, existing_slugs: set, event_id: int = None) -> str:
    """
    Ensure a slug is unique by appending a number if necessary.
    
    Args:
        base_slug: The initial slug to check
        existing_slugs: Set of slugs that already exist
        event_id: The ID of the current event (excluded from duplicate check)
    
    Returns:
        A unique slug, possibly with a numeric suffix
    """
    if not base_slug:
        return None
    
    slug = base_slug
    counter = 1
    
    while slug in existing_slugs:
        counter += 1
        slug = f"{base_slug}-{counter}"
    
    return slug


def generate_event_slug(title: str, date: datetime, db_session, exclude_id: int = None) -> str:
    """
    Generate a unique slug for an event.
    
    Args:
        title: Event title
        date: Event date
        db_session: Database session for checking existing slugs
        exclude_id: Event ID to exclude from duplicate checking (for updates)
    
    Returns:
        A unique, SEO-friendly slug
    """
    from database import Event
    
    # Generate base slug with date
    base_slug = generate_slug(title, date)
    
    if not base_slug:
        # Fallback to event ID if title is empty
        return None
    
    # Get existing slugs from database
    query = db_session.query(Event.slug).filter(Event.slug.isnot(None))
    if exclude_id:
        query = query.filter(Event.id != exclude_id)
    
    existing_slugs = {row[0] for row in query.all()}
    
    # Ensure uniqueness
    return ensure_unique_slug(base_slug, existing_slugs)
