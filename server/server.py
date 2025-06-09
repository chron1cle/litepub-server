#!/usr/bin/env python3
"""
Litepub - minimal read-only “light-web”/EPUB server.

Key improvements
----------------
* **Path traversal protection** – every request is resolved inside
  `content_dir`; anything outside returns *404*.
* **Clear separation of concerns** – routing, auth, HTML→EPUB and helpers
  live in their own methods.
* **PEP-8 style / type-hints / doc-strings** for readability.
* **Fewer global imports** – removed `requests`, `hashlib`, etc.
* **Graceful error handling** with consistent logging.
"""
from __future__ import annotations

import asyncio
import base64
import io
import mimetypes
import re
import ssl
import textwrap
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from aiohttp import web
from bs4 import BeautifulSoup
from lxml import etree

#############################
# Constants & simple helpers
#############################

_CONTAINER_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <container version="1.0"
               xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
      <rootfiles>
        <rootfile full-path="content.opf"
                  media-type="application/oebps-package+xml"/>
      </rootfiles>
    </container>""")

_HTML_TEMPLATE = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta charset="UTF-8"/>
        <title></title>
        <style>
            body {{ font-family: serif; line-height: 1.6; margin: 2em; }}
            img  {{ max-width: 100%; height: auto; display: block; margin: 1em auto; }}
            h1,h2,h3 {{ margin-top: 1.5em; }}
            p   {{ margin: 1em 0; }}
        </style>
    </head>
    <body></body>
    </html>""")

_INDEX_CANDIDATES = ("index.xhtml", "index.html", "index.htm")

################
# Main server
################

@dataclass
class LitepubServer:
    """A tiny HTTPS server that converts (X)HTML files to ad-free EPUBs."""
    host: str = "127.0.0.1"
    port: int = 8181
    cert_path: str = "tests/example-keys/server.crt"
    key_path: str = "tests/example-keys/server.key"
    content_dir: Path | str = "tests/example-content"
    app: web.Application = field(init=False)

    def __post_init__(self) -> None:
        self.content_dir = Path(self.content_dir).resolve()
        self.content_dir.mkdir(exist_ok=True, parents=True)
        self.app = web.Application()
        self.app.router.add_get("/{path:.*}", self.handle_request)

    # --------------------------------------------------------------------- #
    # Request handling
    # --------------------------------------------------------------------- #

    async def handle_request(self, request: web.Request) -> web.StreamResponse:
        """Dispatch a GET request; supports directory listings & EPUB output."""
        raw_path: str = request.match_info["path"]
        safe_path = self._resolve_path(raw_path)

        if safe_path is None:
            return web.Response(status=404, text="Not Found")

        # Directory – serve listing or implicit index file
        if safe_path.is_dir():
            for index_name in _INDEX_CANDIDATES:
                candidate = safe_path / index_name
                if candidate.exists():
                    safe_path = candidate
                    break
            else:
                return await self._render_directory(safe_path, raw_path)

        # *.epub alias – map to underlying xhtml/html
        if safe_path.suffix.lower() == ".epub":
            safe_path = safe_path.with_suffix(".xhtml")

        if not safe_path.exists() or safe_path.is_dir():
            return web.Response(status=404, text="Not Found")

        # Optional Basic-Auth
        auth_resp = await self._check_basic_auth(safe_path, request)
        if auth_resp:
            return auth_resp

        try:
            if safe_path.suffix.lower() in {".html", ".htm"}:
                safe_path = await self._html_to_xhtml(safe_path)

            epub_bytes = await self._xhtml_to_epub(safe_path)
            return web.Response(
                body=epub_bytes,
                headers={
                    "Content-Type": "application/epub+zip",
                    "Content-Length": str(len(epub_bytes)),
                },
            )
        except Exception as exc:  # pragma: no cover
            traceback.print_exc()
            return web.Response(status=500, text=f"Internal Server Error: {exc}")

    # ------------------------------------------------------------------ #
    #  Auth helpers
    # ------------------------------------------------------------------ #

    async def _check_basic_auth(
        self, file_path: Path, request: web.Request
    ) -> Optional[web.Response]:
        """Validate Basic‐Auth credentials if `.auth` file is present.

        `.auth` must contain `user:password` on a single line.
        """
        auth_file = file_path.parent / ".auth"
        if not auth_file.exists():
            return None

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return web.Response(
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Litepub"'},
                text="Unauthorized",
            )

        try:
            decoded = base64.b64decode(auth_header[6:]).decode()
            username, password = decoded.split(":", 1)
            stored_user, stored_pass = auth_file.read_text().strip().split(":", 1)
            if (username, password) != (stored_user, stored_pass):
                raise ValueError("Bad credentials")
        except Exception:
            return web.Response(
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Litepub"'},
                text="Unauthorized",
            )
        return None  # success

    # ------------------------------------------------------------------ #
    #  Directory listing
    # ------------------------------------------------------------------ #

    async def _render_directory(self, dir_path: Path, req_path: str) -> web.Response:
        """Return a simple HTML listing of a directory."""
        links: list[str] = []
        for entry in sorted(p for p in dir_path.iterdir() if not p.name.startswith(".")):
            name = f"{entry.name}{'/' if entry.is_dir() else ''}"
            href = f"{req_path.rstrip('/')}/{entry.name}" if req_path else entry.name
            if entry.is_dir():
                links.append(f'<li><a href="/{href}">{name}</a></li>')
            else:
                epub_href = f"{href.rsplit('.', 1)[0]}.epub"
                links.append(
                    f'<li><a href="/{href}">{name}</a> '
                    f'(<a href="/{epub_href}">epub</a>)</li>'
                )

        parent_link = ""
        if req_path:
            parent = str(Path(req_path).parent)
            parent_link = f'<li><a href="/{"" if parent == "." else parent}">..</a></li>'

        html_page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Directory listing for {req_path}</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;margin:2em}}
ul{{list-style:none;padding:0}}li{{margin:.5em 0}}
a{{text-decoration:none;color:#0366d6}}a:hover{{text-decoration:underline}}
</style></head><body>
<h1>Directory listing for /{req_path}</h1>
<ul>{parent_link}{''.join(links)}</ul></body></html>"""

        return web.Response(text=html_page, content_type="text/html")

    # ------------------------------------------------------------------ #
    #  Path & file utilities
    # ------------------------------------------------------------------ #

    def _resolve_path(self, raw: str) -> Optional[Path]:
        """Return absolute path inside `content_dir`, else *None* (404)."""
        try:
            target = (self.content_dir / raw).resolve()
        except (FileNotFoundError, RuntimeError):
            return None
        # Disallow `..` breakout
        if self.content_dir not in target.parents and target != self.content_dir:
            return None
        return target

    # ------------------------------------------------------------------ #
    #  HTML ➜ cleaned XHTML
    # ------------------------------------------------------------------ #

    async def _html_to_xhtml(self, html_path: Path) -> Path:
        """Strip ads/scripts and save as adjacent `.xhtml` file (idempotent)."""
        xhtml_path = html_path.with_suffix(".xhtml")
        if xhtml_path.exists() and xhtml_path.stat().st_mtime >= html_path.stat().st_mtime:
            return xhtml_path  # already up-to-date

        soup = BeautifulSoup(html_path.read_text("utf-8"), "html.parser")

        # Drop noisy elements
        for tag in soup(["script", "style", "nav", "footer", "iframe"]):
            tag.decompose()

        content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"(?:content|main|article)", re.I))
            or soup.body
        )

        # New clean document
        new = BeautifulSoup(_HTML_TEMPLATE, "xml")
        if (title := soup.title):
            new.title.string = title.string

        if content:
            # Ensure image links are left intact for later EPUB embedding
            new.body.append(content)

        xhtml_path.write_text(str(new), encoding="utf-8")
        return xhtml_path

    # ------------------------------------------------------------------ #
    #  XHTML ➜ EPUB
    # ------------------------------------------------------------------ #

    async def _xhtml_to_epub(self, xhtml_file: Path) -> bytes:
        parser = etree.HTMLParser()
        tree = etree.parse(str(xhtml_file), parser)

        from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

        buf = io.BytesIO()
        with ZipFile(buf, "w", ZIP_DEFLATED) as epub:
            epub.writestr("mimetype", "application/epub+zip", ZIP_STORED)
            epub.writestr("META-INF/container.xml", _CONTAINER_XML)

            # Collect and embed local assets
            embedded_assets = await self._embed_assets(epub, tree, base=xhtml_file.parent)

            # Main document
            epub.writestr("OEBPS/content.xhtml",
                          etree.tostring(tree, encoding="utf-8", method="xml"))

            # OPF with embedded assets in manifest
            epub.writestr("content.opf",
                          self._create_content_opf(xhtml_file.stem, embedded_assets))

        return buf.getvalue()

    async def _embed_assets(
        self, epub: "ZipFile", tree: etree._ElementTree, base: Path
    ) -> dict[str, str]:
        """Embed images referenced by relative paths and rewrite @src.
        
        Returns a dictionary mapping asset paths to their MIME types for manifest generation.
        """
        added: set[str] = set()
        manifest_assets: dict[str, str] = {}

        for el in tree.xpath("//*[@src]"):
            src = el.attrib["src"]
            if src.startswith(("data:", "http://", "https://")):
                continue  # skip remote/data URIs

            asset_path = (base / src).resolve()
            if not asset_path.exists() or self.content_dir not in asset_path.parents:
                continue

            mime = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
            epub_dest = f"OEBPS/{src}"
            if epub_dest not in added:
                epub.writestr(epub_dest, asset_path.read_bytes())
                added.add(epub_dest)
                manifest_assets[src] = mime

            el.attrib["src"] = src  # keep path relative inside EPUB
        
        return manifest_assets

    # --------------------------- OPF helper --------------------------- #

    def _create_content_opf(self, title: str, assets: dict[str, str] = None) -> str:
        """Create OPF manifest file including all embedded assets."""
        if assets is None:
            assets = {}
            
        # Build manifest items for embedded assets
        asset_items = []
        for i, (asset_path, mime_type) in enumerate(assets.items()):
            asset_id = f"asset_{i}"
            asset_items.append(f'    <item id="{asset_id}" href="OEBPS/{asset_path}" media-type="{mime_type}"/>')
        
        asset_manifest = '\n'.join(asset_items)
        if asset_manifest:
            asset_manifest = '\n' + asset_manifest
            
        return textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <package version="3.0" xmlns="http://www.idpf.org/2007/opf">
              <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:title>{title}</dc:title>
                <dc:language>en</dc:language>
                <dc:identifier>urn:uuid:{title}</dc:identifier>
              </metadata>
              <manifest>
                <item id="content" href="OEBPS/content.xhtml"
                      media-type="application/xhtml+xml"/>{asset_manifest}
              </manifest>
              <spine>
                <itemref idref="content"/>
              </spine>
            </package>""")

    # ------------------------------------------------------------------ #
    #  Server bootstrap
    # ------------------------------------------------------------------ #

    async def start(self) -> None:  # pragma: no cover
        """Run the HTTPS server forever."""
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(self.cert_path, self.key_path)

        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port, ssl_context=ssl_ctx)
        await site.start()

        print(f"Litepub running on https://{self.host}:{self.port}")
        while True:
            await asyncio.sleep(3600)


def main() -> None:  # pragma: no cover
    asyncio.run(LitepubServer().start())


if __name__ == "__main__":
    main()
