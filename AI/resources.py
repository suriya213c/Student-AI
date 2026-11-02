import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

try:
    import bs4  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - handled at runtime
    bs4 = None

import urllib3


_MAX_REDIRECTS = 5
_USER_AGENT = "Mozilla/5.0"


def _resolve_public_addresses(host):
    """Resolve a host and reject it unless every address is globally routable."""

    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            records = socket.getaddrinfo(
                host,
                None,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as error:
            raise ValueError("The resource host could not be resolved.") from error

        addresses = []
        for record in records:
            address = record[4][0].split("%", 1)[0]
            addresses.append(ipaddress.ip_address(address))

    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("The resource host must resolve only to public IP addresses.")

    return addresses


def _validate_url(url):
    """Validate a URL and resolve its destination before opening a connection."""

    if not isinstance(url, str) or not url or any(ord(char) < 32 for char in url):
        raise ValueError("The resource URL is invalid.")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("The resource URL is invalid.") from error

    if scheme not in {"http", "https"} or not hostname:
        raise ValueError("Only HTTP and HTTPS resource URLs are allowed.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Resource URLs must not contain credentials.")

    hostname = hostname.rstrip(".").lower()
    if not hostname:
        raise ValueError("The resource URL is invalid.")

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError("The resource host is invalid.") from error

    if port is None:
        port = 443 if scheme == "https" else 80
    if not 1 <= port <= 65535:
        raise ValueError("The resource URL port is invalid.")

    addresses = _resolve_public_addresses(hostname)
    address = addresses[0]

    host_header = f"[{hostname}]" if ":" in hostname else hostname
    if parsed.port is not None:
        host_header = f"{host_header}:{port}"

    request_target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    return scheme, hostname, port, address, host_header, request_target


def _request_pinned(url):
    """Request a URL through a pool connected to its already-validated IP."""

    scheme, hostname, port, address, host_header, request_target = _validate_url(url)
    pool_options = {
        "host": str(address),
        "port": port,
        "timeout": urllib3.Timeout(connect=5, read=10, total=15),
        "retries": False,
        "maxsize": 1,
        "block": True,
    }

    if scheme == "https":
        pool = urllib3.HTTPSConnectionPool(
            **pool_options,
            assert_hostname=hostname,
            server_hostname=hostname,
        )
    else:
        pool = urllib3.HTTPConnectionPool(**pool_options)

    try:
        return pool.request(
            "GET",
            request_target,
            headers={
                "Accept-Encoding": "identity",
                "Host": host_header,
                "User-Agent": _USER_AGENT,
            },
            redirect=False,
            retries=False,
            preload_content=True,
        )
    finally:
        pool.close()


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
        current_url = url
        for redirect_count in range(_MAX_REDIRECTS + 1):
            response = _request_pinned(current_url)
            if response.status not in {301, 302, 303, 307, 308}:
                if response.status >= 400:
                    raise urllib3.exceptions.HTTPError(
                        f"HTTP response status {response.status}"
                    )
                if bs4 is None:
                    raise RuntimeError("BeautifulSoup is required to read web resources.")
                html = response.data
                break

            location = response.headers.get("Location")
            if not location:
                raise urllib3.exceptions.HTTPError(
                    "The resource returned a redirect without a destination."
                )
            if redirect_count == _MAX_REDIRECTS:
                raise urllib3.exceptions.HTTPError("The resource exceeded the redirect limit.")
            current_url = urljoin(current_url, location)
        else:  # pragma: no cover - the loop always exits or raises
            raise urllib3.exceptions.HTTPError("The resource exceeded the redirect limit.")

        soup = bs4.BeautifulSoup(html, "html.parser")

        for element in soup(
            ["script", "style", "noscript"]
        ):
            element.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True
        )
        return text
        return text

    except (OSError, RuntimeError, TypeError, ValueError, urllib3.exceptions.HTTPError) as error:
        return f"RESOURCE_ERROR: {error}"


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
