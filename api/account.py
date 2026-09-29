"""Identity helpers for Wger accounts."""

CONF_USERNAME = "username"


def account_username(profile: dict) -> str:
    """Return the username of the authenticated Wger account."""
    username = profile.get(CONF_USERNAME) if isinstance(profile, dict) else None
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Wger profile does not contain a username")
    return username.strip()


def account_unique_id(url: str, username: str) -> str:
    """Identify an account on a particular Wger server."""
    return f"{url.rstrip('/')}|{username.casefold()}"


def account_title(url: str, username: str) -> str:
    """Name a config entry so multiple accounts remain distinguishable."""
    return f"Wger ({username} @ {url})"
