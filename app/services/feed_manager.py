import feedparser
import httpx


class FeedManager:
    def __init__(self):
        self.headers = {"User-Agent": "reNews-Aggregator/1.0"}

    def fetch_feed_data(self, url: str):
        """
        Fetches the RSS/Atom content from a URL and parses it.
        """
        try:
            response = httpx.get(url, timeout=10.0, headers=self.headers)

            if response.status_code == httpx.codes.OK:
                parsed_data = feedparser.parse(response.text)
            # response.raise_for_status() should use this one?

            if parsed_data.bozo:
                return None

            articles = []
            for entry in parsed_data.entries:
                articles.append(
                    {
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link", "No Link"),
                        "published_date": entry.get("published_parsed", "No Date"),
                    }
                )

            return {
                "feed_title": parsed_data.feed.get("title", "Unknown"),
                "articles": articles,
            }

        except httpx.HTTPStatusError as e:
            print(f"Server error {e.response.status_code} while fetching {url}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


# To test it (manually):
manager = FeedManager()
print(manager.fetch_feed_data("https://news.ycombinator.com/rss"))
