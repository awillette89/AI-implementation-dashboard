"""Request the public Streamlit app so its host sees periodic activity.

GitHub Actions supplies STREAMLIT_APP_URL as a repository variable. Keeping the
URL outside this script means a new deployment address does not require a code
change.
"""

from __future__ import annotations

import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class DoNotFollowRedirects(HTTPRedirectHandler):
    """Keep the first response so a host redirect cannot create a request loop."""

    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def get_app_url() -> str:
    """Read and lightly validate the deployment URL from GitHub Actions."""
    app_url = os.environ.get("STREAMLIT_APP_URL", "").strip()
    parsed_url = urlparse(app_url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError(
            "Set the STREAMLIT_APP_URL repository variable to the full public "
            "address, for example https://your-app.streamlit.app"
        )

    return app_url


def main() -> int:
    """Make one request and return a nonzero status if the app cannot be reached."""
    try:
        app_url = get_app_url()
        # A recognizable User-Agent helps the app host identify this scheduled request.
        request = Request(app_url, headers={"User-Agent": "github-actions-streamlit-keep-awake"})
        # A 3xx redirect still shows that the public app host received this ping.
        # We deliberately do not follow it because some Streamlit hosts redirect
        # automated requests back to the same public address.
        opener = build_opener(DoNotFollowRedirects)
        with opener.open(request, timeout=30) as response:
            print(f"Requested {response.url} and received HTTP {response.status}.")
    except HTTPError as error:
        if 300 <= error.code < 400:
            print(f"Requested {error.url} and received redirect HTTP {error.code}.")
            return 0

        print(f"Could not request the Streamlit app: {error}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ValueError) as error:
        print(f"Could not request the Streamlit app: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
