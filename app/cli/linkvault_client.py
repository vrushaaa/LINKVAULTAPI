"""
linkvault_client - command-line client for LinkVault API
Usage:
    python linkvault_client.py <command> [options]
"""

import click
import requests
import json
from urllib.parse import urlencode
import os

BASE_URL = "http://127.0.0.1:5000"   # change if you run on another host/port

def _print(resp: requests.Response):
    click.echo(f"Status: {resp.status_code}")
    try:
        click.echo(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        click.echo(resp.text)

@click.group(help="LinkVault API client - CRUD + export/import")
def cli():
    pass


def _split_tags(tags):
    result = []
    for t in tags:
        result.extend([x.strip() for x in t.split(",") if x.strip()])
    return result


@cli.command()
@click.argument("url")
@click.option("--title", help="Bookmark title")
@click.option("--notes", help="Notes")
@click.option(
    "--tags",
    multiple=True,
    help="Tags - repeat the flag OR give a comma-separated list",
)
@click.option("--archived", is_flag=True, help="Mark as archived")
def create(url, title, notes, tags, archived):
    """POST /api/bookmarks - add a new bookmark."""
    tags = _split_tags(tags)               
    payload = {
        "url": url,
        "title": title or None,
        "notes": notes or None,
        "tags": tags or None,
        "archived": archived,
    }
    r = requests.post(f"{BASE_URL}/api/bookmarks", json=payload)
    _print(r)


@cli.command()
@click.option("--page", default=1, type=int, help="Page number")
@click.option("--per-page", default=10, type=int, help="Items per page")
@click.option("--tag", help="Filter by tag")
@click.option("--q", help="Search keyword")
@click.option("--archived", is_flag=True, help="Show only archived")
def list(page, per_page, tag, q, archived):
    """GET /api/bookmarks - list bookmarks."""
    params = {
        "page": page,
        "per_page": per_page,
        "tag": tag,
        "q": q,
        "archived": "true" if archived else None,
    }
    
    params = {k: v for k, v in params.items() if v is not None}
    r = requests.get(f"{BASE_URL}/api/bookmarks?{urlencode(params)}")
    _print(r)


@cli.command()
@click.argument("bookmark_id", type=int)
@click.option("--title", help="New title")
@click.option("--notes", help="New notes")
@click.option("--tags", multiple=True, help="New tags - repeat OR use comma list")
@click.option("--archived", is_flag=True, help="Set archived")
@click.option("--unarchive", is_flag=True, help="Unset archived")
def update(bookmark_id, title, notes, tags, archived, unarchive):
    """PUT /api/bookmarks/<id> - partial update."""
    
    final_tags = []
    for t in tags:
        final_tags.extend([x.strip() for x in t.split(",") if x.strip()])

    payload = {}
    if title is not None:
        payload["title"] = title
    if notes is not None:
        payload["notes"] = notes
    if final_tags:
        payload["tags"] = final_tags
    if archived:
        payload["archived"] = True
    if unarchive:
        payload["archived"] = False

    r = requests.put(f"{BASE_URL}/api/bookmarks/{bookmark_id}", json=payload)
    _print(r)


@cli.command()
@click.argument("bookmark_id", type=int)
def delete(bookmark_id):
    """DELETE /api/bookmarks/<id>."""
    r = requests.delete(f"{BASE_URL}/api/bookmarks/{bookmark_id}")
    _print(r)


@cli.command()
@click.argument("bookmark_id", type=int)
def toggle_archive(bookmark_id):
    """PATCH /api/bookmarks/<id>/archive."""
    r = requests.patch(f"{BASE_URL}/api/bookmarks/{bookmark_id}/archive")
    _print(r)


@cli.command()
@click.argument("output_file", type=click.Path())
def export(output_file):
    """GET /api/export - download Netscape HTML."""
    r = requests.get(f"{BASE_URL}/api/export", stream=True)
    if r.status_code != 200:
        _print(r)
        return

    with open(output_file, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    click.echo(f"Exported to {output_file}")


@cli.command()
@click.option("--page", default=1, type=int, help="Page number")
@click.option("--per-page", default=10, type=int, help="Items per page")
@click.option("--tag", multiple=True, help="Filter by tags (repeat --tag)")
@click.option("--q", help="Search keyword")
@click.option("--archived", is_flag=True, help="Show only archived")
@click.option("--id", type=int, help="Filter by bookmark ID")
def list(page, per_page, tag, q, archived, id):
    """GET /api/bookmarks - list bookmarks."""
    params = {
        "page": page,
        "per_page": per_page,
        "q": q,
        "archived": "true" if archived else None,
        "id": id,
    }
    if tag:
        params["tag"] = ",".join(tag)

    params = {k: v for k, v in params.items() if v is not None}
    
    url = f"{BASE_URL}/api/bookmarks"
    if params:
        url += "?" + urlencode(params)
    
    r = requests.get(url)
    _print(r)


if __name__ == "__main__":
    cli()