"""Keep secrets out of what callscope prints."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SENSITIVE = re.compile(
    r"(pass(word|wd)?|secret|token|api[-_]?key|key|auth|signature|sig|session|credential|code)",
    re.IGNORECASE,
)
MASK = "***"


def redact_url(url: str) -> str:
    """Mask passwords in the netloc and values of sensitive query parameters."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    netloc = parts.netloc
    if "@" in netloc:
        userinfo, host = netloc.rsplit("@", 1)
        user = userinfo.split(":", 1)[0]
        netloc = f"{user}:{MASK}@{host}" if ":" in userinfo else f"{user}@{host}"
    query = parts.query
    if query:
        pairs = parse_qsl(query, keep_blank_values=True)
        query = urlencode([(k, MASK if _SENSITIVE.search(k) else v) for k, v in pairs], safe="*")
    return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))
