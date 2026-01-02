# Scrapy settings for scraper project

BOT_NAME = "scraper"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

ADDONS = {}

# 🚨 Ignorar robots.txt para poder scrapear Reddit
ROBOTSTXT_OBEY = False

# ⚡ Controlar la velocidad de scraping
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2   # espera 2 segundos entre requests

# 📌 Usar un User-Agent realista para que parezca un navegador normal
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Encoding de los archivos exportados
FEED_EXPORT_ENCODING = "utf-8"
