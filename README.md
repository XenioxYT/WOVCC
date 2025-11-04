# WOVCC Website

Professional cricket club website with Python backend API for Wickersley Old Village Cricket Club.

## 🎯 Project Overview

A professional, production-ready website with Python backend API. Features:

- Professional glassmorphism design with Inter font
- Python Flask API with Play-Cricket web scraping
- Smart match display (live scores vs fixtures/results)
- User dropdown menu with authentication
- Team filtering and selection
- Real-time data with automatic refresh
- Mobile-responsive design
- Ready for VPS deployment

## 📁 Project Structure

```
WOVCC/
├── backend/                        # Python Flask API
│   ├── api.py                     # API server
│   ├── scraper.py                 # Play-Cricket scraper
│   ├── requirements.txt           # Python dependencies
│   ├── wovcc-api.service          # Systemd service
│   ├── nginx.conf                 # Nginx configuration
│   └── README.md                  # Backend documentation
│
├── index.html                     # Homepage with smart match display
├── pages/
│   ├── join.html                 # Join membership
│   └── members.html              # Members area
├── scripts/
│   ├── auth.js                   # Authentication with dropdown
│   ├── main.js                   # General functionality
│   ├── api-client.js             # API communication
│   └── match-controller.js       # Match display logic
├── styles/
│   ├── main.css                  # Professional glassmorphism design
│   └── pages.css                 # Page-specific styles
├── assets/
│   ├── logo.png
│   └── banner.jpeg
│
├── DEPLOYMENT.md                  # Full deployment guide
├── IMPLEMENTATION_SUMMARY.md      # Complete feature list
└── README.md                      # This file
```

## 🎨 Design

**Colors:**
- Primary: `#1a5f5f` (Dark Teal)
- Accent: `#d4a574` (Gold)

**Typography:**
- Font: Inter (Google Fonts)
- Professional, clean, modern

**Effects:**
- Glassmorphism (frosted glass)
- Blur effects (backdrop-filter)
- Smooth transitions
- Hover states

## 🚀 Getting Started

### Frontend (Local Development)

Simply open `index.html` in a web browser. No build process needed.

### Backend (Local Development)

```bash
cd backend
pip install -r requirements.txt
python api.py
```

API runs on `http://localhost:5000`

## 📄 Pages

### Homepage (`index.html`)
- Hero section with club branding
- Smart match display:
  - **Match Day:** Livestream + Play-Cricket live scores
  - **No Matches:** Upcoming fixtures + Recent results
- Team selector for filtering
- Club information cards

### Join (`pages/join.html`)
- £15/year membership
- Benefits list
- New member signup
- Payment via Stripe Checkout

### Members Area (`pages/members.html`)
- Login gate
- Member dashboard
- User dropdown in navbar

## 🔐 Features

### Smart Match Display
- Automatically checks if matches are happening today
- Shows livestream and scores during matches
- Shows fixtures and results when no matches
- Polls every 5 minutes for updates

### User Authentication
- Mock system using localStorage
- Dropdown menu shows when logged in
- Displays user's name
- Logout functionality
- **Note:** For production, implement proper backend auth!

### Team Filtering
- Filter fixtures/results by team
- Dropdown populated from API
- "All Teams" default option
- 1st XI, 2nd XI, Vixens, etc.

### API Integration
- Fetches real-time data from backend
- Renders beautiful cards for fixtures/results
- Error handling and fallbacks
- Automatic refresh

## 🏏 Backend API

### Endpoints

- `GET /api/health` - Health check
- `GET /api/teams` - List all teams
- `GET /api/fixtures?team=all` - Upcoming fixtures
- `GET /api/results?team=all&limit=10` - Recent results
- `GET /api/match-status` - Check if matches today
- `POST /api/clear-cache` - Clear cached data

### Features

- Web scraping of Play-Cricket pages
- 6-hour data caching
- CORS enabled
- Error handling
- Production-ready

## 🚀 Deployment

### Quick Start

1. **Deploy Backend to VPS:**
   ```bash
   # Upload files
   scp -r backend/* user@vps:/var/www/wovcc-api/
   
   # Install dependencies
   ssh user@vps
   cd /var/www/wovcc-api
   pip3 install -r requirements.txt
   
   # Setup systemd service
   sudo cp wovcc-api.service /etc/systemd/system/
   sudo systemctl enable wovcc-api
   sudo systemctl start wovcc-api
   
   # Configure Nginx (use provided nginx.conf)
   sudo nano /etc/nginx/sites-available/wovcc-api
   sudo systemctl reload nginx
   
   # Setup SSL
   sudo certbot --nginx -d api.wovcc.co.uk
   ```

2. **Deploy Frontend:**
   - Upload to VPS or static hosting (Netlify, Vercel, etc.)
   - Update API URL in `scripts/api-client.js`
   - Test functionality

3. **Full Instructions:**
   See `DEPLOYMENT.md` for complete step-by-step guide.

## ⚙️ Configuration

### API URL

Edit `scripts/api-client.js`:

```javascript
const API_CONFIG = {
  baseURL: 'https://api.wovcc.co.uk/api',  // Change to your domain
  timeout: 10000
};
```

### YouTube Livestream

Edit `index.html`:

```html
<iframe src="https://www.youtube.com/embed/YOUR_STREAM_ID" ...>
```

### Club ID

Already set to 6908 (Wickersley Old Village CC) in scraper.

## 📊 What's Different

### Removed
- All emojis
- Educational/example pages
- Multiple navigation items
- Basic styling

### Added
- Python backend API
- Web scraping functionality
- Professional glassmorphism design
- Smart match display logic
- User dropdown menu
- Team filtering
- Modern Inter font
- Deployment configuration

### Improved
- Performance (6-hour caching)
- User experience (glanceable data)
- Mobile responsiveness
- Professional appearance
- Navigation (cleaner)

## 📱 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers

## 📚 Documentation

- `DEPLOYMENT.md` - Full deployment guide with systemd, Nginx, SSL
- `IMPLEMENTATION_SUMMARY.md` - Complete feature list and technical details
- `backend/README.md` - Backend API documentation

## 🛠️ Technology Stack

**Backend:**
- Python 3.8+
- Flask (web framework)
- BeautifulSoup4 (web scraping)
- Requests (HTTP)

**Frontend:**
- HTML5
- CSS3 (Glassmorphism, Grid, Flexbox)
- Vanilla JavaScript (ES6+)
- Google Fonts (Inter)

**Deployment:**
- Systemd (service management)
- Nginx (reverse proxy)
- Let's Encrypt (SSL)

## 🔒 Security

- HTTPS/SSL enforced
- CORS configured
- Input validation
- Error handling
- **Note:** Implement proper authentication for production!

## 📞 Support

Check logs:
```bash
sudo journalctl -u wovcc-api -f
```

Test API:
```bash
curl https://api.wovcc.co.uk/api/health
```

## 📝 License

Private project for Wickersley Old Village Cricket Club.

---

**Version:** 2.0 (Production Ready)  
**Last Updated:** October 31, 2025  
**Status:** Ready for Deployment

