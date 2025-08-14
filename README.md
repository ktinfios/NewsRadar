# NewsRadar 

A simple web-based dashboard for the NewsRadar news monitoring application.

## Features

### 📊 Dashboard
- **Real-time Statistics**: View total articles, tracked companies, and key terms
- **Recent Articles**: Browse the latest news articles with company and key term filters
- **Search Status**: Monitor manual search progress with real-time updates
- **Manual Search**: Trigger news searches directly from the web interface

### ⚙️ Settings
- **Configuration Overview**: View current companies and key terms being tracked
- **System Information**: Check Python version, environment status, and web interface details
- **File Management**: Access to download data files and view logs
- **Email Configuration**: Information about email setup requirements

## Quick Start

### 1. Install Required Packages
```powershell
pip install requirements.txt
```

### 2. Start the Web Interface
```powershell
python start_web.py
```

### 3. Access the Dashboard
Open your web browser and navigate to:
- **Local Access**: http://localhost:5000
- **Network Access**: http://0.0.0.0:5000 (for access from other devices)

## Usage

### Manual Search
1. Go to the Dashboard
2. Click the "Manual Search" button
3. Monitor the search progress in real-time
4. View new articles automatically loaded after search completion

### View Articles
- Articles are displayed as cards with company, key term, and publication date
- Click "Read Article" to open the full article in a new tab
- Use the "Refresh" button to reload articles without a full page refresh

### Monitor Status
- Green indicator: System ready
- Yellow (pulsing): Search in progress
- Red: Error occurred

## API Endpoints

The web interface provides several REST API endpoints:

- `GET /api/articles?limit=20` - Fetch recent articles
- `POST /api/search` - Trigger manual search
- `GET /api/search/status` - Get current search status
- `GET /api/stats` - Get system statistics

## File Structure

```
NewsRadar/
├── web_app.py              # Main Flask application
├── start_web.py            # Startup script
├── templates/
│   ├── dashboard.html      # Main dashboard page
│   └── settings.html       # Settings and configuration page
├── NewsRadar.py            # Core news search functionality
└── news_articles.csv       # Article data storage
```

## Configuration

### Email Settings
Configure email functionality through environment variables:
- `SENDER_EMAIL`: Your Gmail address
- `SENDER_PASSWORD`: App password for Gmail account

### Search Parameters
Modify search parameters in `NewsRadar.py`:
- `COMPANIES`: List of companies to monitor
- `KEY_TERMS`: List of key terms to search for
- `ARTICLE_AGE_DAYS`: Maximum age of articles to include

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure Flask is installed: `pip install flask flask-cors`
   - Check that you're in the correct directory

2. **Port Already in Use**
   - Change the port in `web_app.py`: `app.run(port=5001)`
   - Or kill existing processes using port 5000

3. **No Articles Displayed**
   - Run a manual search first
   - Check that `news_articles.csv` exists and contains data

4. **Search Fails**
   - Check internet connection
   - Verify that all required packages are installed
   - Check `app.log` for detailed error messages

### Development Mode

The web interface runs in debug mode by default, which provides:
- Automatic reloading when files change
- Detailed error messages
- Enhanced logging

To disable debug mode, modify `web_app.py`:
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

## Security Notes

- The web interface binds to `0.0.0.0` for network access
- For production use, consider adding authentication
- Sensitive email credentials should be properly secured in environment variables

## Browser Compatibility

Tested and compatible with:
- Chrome/Chromium 80+
- Firefox 75+
- Safari 13+
- Edge 80+

The interface uses Bootstrap 5 and modern JavaScript features.