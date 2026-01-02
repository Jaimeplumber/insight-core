import scrapy
import json

class RedditSpider(scrapy.Spider):
    name = "reddit_spider"
    start_urls = ["https://www.reddit.com/r/AskReddit/.json"]

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
    }

    def parse(self, response):
        data = json.loads(response.text)
        for post in data['data']['children']:
            yield {
                'title': post['data']['title'],
                'author': post['data']['author'],
                'score': post['data']['score'],
                'url': post['data']['url'],
                'comments': post['data']['num_comments'],
            }

        # Paginación
        after = data['data'].get('after')
        if after:
            next_page = f"{response.url.split('?')[0]}?after={after}"
            yield response.follow(next_page, callback=self.parse)
