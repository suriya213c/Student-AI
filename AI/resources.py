import re
import requests
from urllib.parse import urlparse

try:
    import bs4  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - handled at runtime
    bs4 = None


def detect_resource_type(url):
    """Identify the type of online study resource."""

    url = url.strip().lower()

    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"

    if "drive.google.com" in url:
        return "Google Drive"

    return "Web Resource"


def extract_youtube_id(url):
    """Extract YouTube video ID."""

    patterns = [
        r"(?:youtube\.com/watch\?v=)([^&]+)",
        r"(?:youtu\.be/)([^?&]+)",
        r"(?:youtube\.com/embed/)([^?&]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


def get_youtube_info(url):
    """Get basic YouTube video information."""

    video_id = extract_youtube_id(url)

    if not video_id:
        return None

    return {
        "type": "YouTube",
        "video_id": video_id,
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
        "watch_url": url,
    }


def get_webpage_text(url):
    """Extract readable text from a webpage."""

    try:

        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        soup = bs4.BeautifulSoup(
            response.text,
            "html.parser"
        )

        for element in soup(
            ["script", "style", "noscript"]
        ):
            element.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        return text

    except Exception as e:

        return f"RESOURCE_ERROR: {e}"


def analyze_resource(url):
    """Analyze a study resource URL."""

    resource_type = detect_resource_type(url)

    if resource_type == "YouTube":

        return get_youtube_info(url)

    if resource_type == "Google Drive":

        return {
            "type": "Google Drive",
            "url": url,
            "message": (
                "Google Drive resource detected. "
                "If the file is publicly accessible, "
                "it can be processed."
            ),
        }

    text = get_webpage_text(url)

    return {
        "type": "Web Resource",
        "url": url,
        "text": text,
    }