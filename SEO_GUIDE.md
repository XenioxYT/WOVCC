# WOVCC SEO Implementation Guide

This document outlines the SEO (Search Engine Optimization) implementation for the Wickersley Old Village Cricket Club website.

## Table of Contents

1. [SEO Implementation Overview](#seo-implementation-overview)
2. [Page-by-Page SEO Audit](#page-by-page-seo-audit)
3. [Technical SEO Files](#technical-seo-files)
4. [Structured Data (Schema.org)](#structured-data-schemaorg)
5. [Ongoing Maintenance](#ongoing-maintenance)

---

## SEO Implementation Overview

### Global SEO Features (layout.html)

All pages inherit these SEO features from the base template:

| Feature | Implementation | Status |
|---------|----------------|--------|
| **Meta Description** | Jinja block, customizable per page | ✅ |
| **Title Tag** | Jinja block, customizable per page | ✅ |
| **Robots Meta Tag** | Jinja block, defaults to `index, follow` | ✅ |
| **Author Meta** | "Wickersley Old Village Cricket Club" | ✅ |
| **Theme Color** | `#1a5f5f` (brand color) | ✅ |
| **Geo Meta Tags** | Region, placename, coordinates | ✅ |
| **Favicons** | Multiple sizes (16x16, 32x32, apple-touch) | ✅ |
| **Open Graph** | Type, URL, title, description, image (with dimensions & alt) | ✅ |
| **Twitter Cards** | Card type, site, creator, title, description, image (with alt) | ✅ |
| **Canonical URL** | Auto-generated from `site_base_url` + path | ✅ |
| **Preconnect** | Google Fonts (googleapis, gstatic) | ✅ |
| **Preload** | Critical scripts | ✅ |
| **SportsClub Schema** | Full organization data on every page | ✅ |
| **WebSite Schema** | With SearchAction for sitelinks | ✅ |
| **BreadcrumbList Schema** | Customizable per page | ✅ |

---

## Page-by-Page SEO Audit

### ✅ Public Pages (Indexed)

| Page | Title | Description | Breadcrumbs | Schema | Robots |
|------|-------|-------------|-------------|--------|--------|
| **Homepage** (`index.html`) | ✅ Keyword-rich | ✅ Comprehensive with address | ✅ None (root) | ✅ Global | `index, follow` |
| **Events** (`events.html`) | ✅ "Club Events & What's On" | ✅ Dynamic with event names | ✅ Home > Events | ✅ ItemList of Events | `index, follow` |
| **Event Detail** (`event-detail.html`) | ✅ Event name in title | ✅ With date | ✅ Home > Events > [Name] | ✅ Event schema | `index, follow` |
| **Matches** (`matches.html`) | ✅ "Cricket Fixtures & Results" | ✅ Dynamic with counts | ✅ Home > Matches | ✅ SportsOrganization | `index, follow` |
| **Join** (`join.html`) | ✅ Price in title "£15/Year" | ✅ Benefits & pricing | ✅ Home > Join | ✅ Product schema | `index, follow` |
| **Contact** (`contact.html`) | ✅ Standard | ✅ With phone, email, address | ✅ Home > Contact | ✅ ContactPage schema | `index, follow` |
| **Privacy** (`privacy.html`) | ✅ Standard | ✅ Mentions UK GDPR | ✅ Home > Privacy | ✅ Global | `index, follow` |

### ❌ Private Pages (Not Indexed)

| Page | Title | Description | Robots |
|------|-------|-------------|--------|
| **Login** (`login.html`) | ✅ "Member Login" | ✅ | `noindex, nofollow` |
| **Membership** (`membership.html`) | ✅ "My Membership" | ✅ | `noindex, nofollow` |
| **Members** (`members.html`) | ✅ "Members Area" | ✅ | `noindex, nofollow` |
| **Admin** (`admin.html`) | ✅ "Admin Panel" | ✅ | `noindex, nofollow` |
| **Activate** (`activate.html`) | ✅ Standard | ✅ | `noindex, nofollow` |
| **Cancel** (`cancel.html`) | ✅ Standard | ✅ | `noindex, nofollow` |
| **404** (`404.html`) | ✅ "Page Not Found" | ✅ | `noindex, nofollow` |
| **500** (`500.html`) | ✅ "Server Error" | ✅ | `noindex, nofollow` |

---

## Technical SEO Files

### robots.txt (`/robots.txt`)

**Location:** `app.py` → `robots()` function

```
User-agent: *
Allow: /

# Allow public API endpoints
Allow: /api/events
Allow: /api/data
Allow: /api/sponsors
...

# Block sensitive endpoints
Disallow: /api/auth/
Disallow: /api/admin/
Disallow: /admin
Disallow: /login
Disallow: /membership
...

Sitemap: https://wickersleycricket.com/sitemap.xml
```

### sitemap.xml (`/sitemap.xml`)

**Location:** `app.py` → `sitemap()` function

**Included Pages:**
- `/` (priority 1.0, daily)
- `/events` (priority 0.9, daily)
- `/matches` (priority 0.8, daily)
- `/join` (priority 0.7, monthly)
- `/contact` (priority 0.6, monthly)
- `/privacy` (priority 0.3, yearly)
- All published events dynamically (priority 0.7 upcoming, 0.5 past)

---

## Structured Data (Schema.org)

### Global Schema (All Pages)

**SportsClub Organization** - Full business information:
- Name, alternate names, URL, logo, image
- Address (59 Northfield Lane, Wickersley, S66 2HL)
- Coordinates (53.4147, -1.2978)
- Phone, email
- Opening hours (all days)
- Social profiles (Facebook, Instagram, X, Play-Cricket)
- League membership (Yorkshire Cricket Southern Premier League)
- Membership offering (£15/year)

**WebSite** - With SearchAction for sitelinks search box

**BreadcrumbList** - Customized per page

### Page-Specific Schema

| Page | Schema Type | Key Data |
|------|-------------|----------|
| **Events List** | ItemList | All events with dates, locations, organizer |
| **Event Detail** | Event | Full event details, status, attendance mode |
| **Matches** | SportsOrganization | Team info, league, location |
| **Join** | Product | Membership pricing, availability |
| **Contact** | ContactPage + ContactPoint | Phone, email, areas served, hours |

---

## Ongoing Maintenance

### Best Practices for New Events

When creating events, optimize for SEO:

1. **Title**: Include keywords (e.g., "New Year's Eve Party at WOVCC Cricket Club")
2. **Short Description**: 150-160 characters, include key details
3. **Image**: Always upload a relevant image (helps with social sharing)
4. **Date/Time**: Always fill in accurately (used in schema)
5. **Location**: Specify if different from main clubhouse

### Monthly SEO Checklist

- [ ] Check Google Search Console for crawl errors
- [ ] Review "Coverage" for indexing issues
- [ ] Check "Performance" for top queries
- [ ] Verify sitemap is up to date
- [ ] Test rich results: https://search.google.com/test/rich-results

### Testing Tools

- **Rich Results Test**: https://search.google.com/test/rich-results
- **Schema Validator**: https://validator.schema.org/
- **Facebook Debugger**: https://developers.facebook.com/tools/debug/
- **Twitter Card Validator**: https://cards-dev.twitter.com/validator

---

## File Reference

| File | Purpose |
|------|---------|
| `backend/templates/layout.html` | Base template with global SEO |
| `backend/app.py` | robots.txt, sitemap.xml, config |
| `backend/routes_pages.py` | Page routes with server-side data for SEO |
| Individual page templates | Page-specific SEO blocks |

---

*Last updated: December 2024*
