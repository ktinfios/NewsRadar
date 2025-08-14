# NewsRadar 

A simple web-based application that searches the web for relevant articles to companies based on specified key terms. After finding the articles, NewsRadar uses natural language processing to summarize each of the articles and then emails these summaries to the user.

## Features
- **Real-time Statistics**: View total articles, tracked companies, and key terms
- **Recent Articles**: Browse the latest news articles with company and key term filters
- **Search Status**: Monitor manual search progress with real-time updates
- **Custom Search**: Specify what companies and key terms to search for
- **Email**: Automatically email the articles and their summaries to the specified email

## Quick Start

### 1. Install Required Packages
```powershell
pip install -r requirements.txt
```

### 2. Start the Web Interface
```powershell
python start_web.py
```

### 3. Access the Dashboard
Open your web browser and navigate to: http://localhost:5000

## Usage

### Search
2. Click the "Manual Search" button
3. Monitor the search progress in real-time
4. View new articles automatically loaded after search completion

### View Articles
- Articles are displayed as cards with company, key term, and publication date
- Click "Read Article" to open the full article in a new tab
- Use the "Refresh" button to reload articles without a full page refresh

### Monitor Status
- Green: System ready
- Yellow : Search in progress
- Red: Error occurred

## Configuration

### Email Settings
Configure email functionality through environment variables:
- `SENDER_EMAIL`: Your Gmail address
- `SENDER_PASSWORD`: App password for Gmail account

### Search Parameters
Modify search parameters in `NewsRadar.py`:
- `COMPANIES`: Default list of companies to monitor
- `KEY_TERMS`: Default list of key terms to search for
- `ARTICLE_AGE_DAYS`: Maximum age of articles to include

## Future Improvements

- Add functionality to specify what email to send to 
   - Currently defined in the .env file and uses sender email 
- Fine tune an tranformer model or other neural network (like [Pegasus](https://huggingface.co/docs/transformers/en/model_doc/pegasus)) to produce better summarizes 
- Find a way to speed up the current NLP portion of the application 
   - NLP is expensive, so finding ways to speed up how this is done would speed up the overall application
- Find a way to handle pay wall summaries 

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