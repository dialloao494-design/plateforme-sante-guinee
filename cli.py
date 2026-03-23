import json
import os
import urllib.request
import urllib.parse

import click

TOKEN_FILE = ".clinetoken"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def save_token(token: str):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token)


def load_token() -> str | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def request_json(url: str, data=None, headers=None):
    if headers is None:
        headers = {}

    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


@click.group()
def cli():
    """CLI helper for the health platform."""


@cli.command("signin")
@click.option("--email", prompt=True, help="User email")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=False, help="User password")
@click.option("--base-url", default=DEFAULT_BASE_URL, show_default=True, help="API base URL")
def sign_in(email, password, base_url):
    """Sign in and save bearer token locally."""
    try:
        result = request_json(f"{base_url}/auth/signin", data={"username": email, "password": password})
        access_token = result.get("access_token")
        if not access_token:
            click.echo("Sign-in failed: no token returned")
            raise SystemExit(1)
        save_token(access_token)
        click.echo("Signed in successfully. Token saved to %s" % TOKEN_FILE)
    except urllib.error.HTTPError as exc:
        content = exc.read().decode("utf-8")
        click.echo(f"Sign-in failed ({exc.code}): {content}")
        raise SystemExit(1)
    except Exception as exc:
        click.echo(f"Sign-in failed: {exc}")
        raise SystemExit(1)


@cli.command("whoami")
@click.option("--base-url", default=DEFAULT_BASE_URL, show_default=True, help="API base URL")
def whoami(base_url):
    """Show current user from token."""
    token = load_token()
    if not token:
        click.echo("No token found. Run sign-in first.")
        raise SystemExit(1)

    try:
        result = request_json(f"{base_url}/auth/me", headers={"Authorization": f"Bearer {token}"})
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as exc:
        content = exc.read().decode("utf-8")
        click.echo(f"whoami failed ({exc.code}): {content}")
        raise SystemExit(1)


@cli.command("signout")
def sign_out():
    """Remove local token."""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        click.echo("Signed out and removed local token.")
    else:
        click.echo("No token file exists.")


if __name__ == "__main__":
    cli()
