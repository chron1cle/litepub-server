# 📘 Litepub Protocol Specification & Server Implementation (v0.1 Draft)

## Overview

Litepub is a lightweight, encrypted, and privacy-respecting protocol designed for serving self-contained EPUB content in place of modern web pages. It combines the simplicity of Gemini with the layout capabilities of EPUB, using a wire-level protocol similar to HTTP.

This repository contains both the protocol specification and a Python-based reference server implementation.

---

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Generate TLS certificates:
```bash
python server/generate_cert.py
```

3. Start the server:
```bash
python server/server.py
```

4. Visit `https://localhost:8181` in your browser

The server will serve content from `tests/example-content/` by default, automatically converting HTML/XHTML files to EPUB format.

---

## Goals

- Free and open: no gatekeepers or CA requirements
- Encrypted by default with TOFU (Trust On First Use)
- Serve EPUB 3.2 bundles for each page
- Minimal, efficient, and easy to implement

---

## URI Scheme

```
https://hostname[:port]/path/to/page
```

- Default port: `8181`

---

## Transport

- All connections must be encrypted
- TLS is required (TLS 1.2+)
- No CA verification required
- Self-signed certificates are accepted
- Clients use TOFU: trust the server's certificate fingerprint on first connection and alert on future mismatch

---

## Wire-Level Protocol (HTTPS-based)

### Request Format

```
GET /path/to/page.epub HTTP/1.1
Host: example.org
```

### Response Format

```
HTTP/1.1 200 OK
Content-Type: application/epub+zip
Content-Length: 123456

(binary EPUB data)
```

*Note: Future versions may include a `X-Litepub-Protocol: 1.0` header to explicitly identify Litepub responses.*

### Response Codes

| Code                      | Meaning                               |
|---------------------------|----------------------------------------|
| 200 OK                    | Successful response with EPUB payload  |
| 301 Moved Permanently     | Page has moved (new Location header)   |
| 302 Found                 | Temporary redirect                     |
| 400 Bad Request           | Malformed request                      |
| 403 Forbidden             | Access denied                          |
| 404 Not Found             | Resource not found                     |
| 500 Internal Server Error | Unexpected server failure              |

---

## Content Format

- MIME type: `application/epub+zip`
- All pages are served as EPUB 3.2 files
- All resources must be embedded in the EPUB
- Navigation occurs via standard EPUB hyperlinks between pages

---

## Authentication and Identity

- **TOFU (Trust On First Use)**
  - Clients store the server's certificate fingerprint on first connection
  - If the key changes, users are prompted to accept or reject the new fingerprint

- **Stateless Authentication**
  - No cookie-based sessions
  - Use classic HTTP-style headers:
    - `Authorization: Basic <base64(user:pass)>`
    - Server responds with `401 Unauthorized` and `WWW-Authenticate: Basic realm="Litepub"` if credentials are missing or invalid
  - Stateless and cookie-free by design
  - Avoids form posts or embedded login pages

- No login forms or passwords in the protocol layer (may be included within content if necessary)

---

## Hosting Considerations

- **Static Hosting:**
  - Site authors may pre-package and serve `.epub` files directly

- **Dynamic Hosting (default):**
  - Server dynamically converts `.xhtml` and associated assets into valid EPUB 3.2 files upon request
  - Facilitates easier maintenance for authors using plain XHTML content
  - All required resources (images, CSS, fonts, etc.) are resolved by parsing the XHTML and identifying linked assets
  - No fixed file structure is required as long as referenced assets are accessible relative to the .xhtml file
  - Convert existing html in to epub on the fly for quicker integration with existing websites

- **Directory Behavior:**
  - If a request targets a directory, serve `index.xhtml` as `index.epub` by default, similar to modern browser behavior

---

## Server Implementation

This repository includes a Python-based reference server implementation that:

- Implements the Litepub protocol specification
- Dynamically converts HTML/XHTML to EPUB format
- Supports TLS with self-signed certificates
- Provides Basic authentication for protected content
- Automatically embeds referenced assets (images, CSS, etc.)
- Offers directory browsing with automatic EPUB conversion links
- Cleans HTML content by removing ads, scripts, and navigation elements

### Server Features

- **Async HTTP handling** with `aiohttp`
- **HTML sanitization** removes scripts, ads, and navigation elements
- **Asset embedding** automatically includes referenced images and stylesheets
- **Path traversal protection** prevents access outside content directory
- **Automatic XHTML conversion** from HTML with content extraction
- **Directory listings** with EPUB download links
- **Basic authentication** via `.auth` files

### File Structure

```
litepub-server/
├── README.md                 # This file (protocol spec & server docs)
├── requirements.txt          # Python dependencies
├── server/
│   ├── README.md            # Server-specific documentation
│   ├── server.py            # Main server implementation
│   └── generate_cert.py     # TLS certificate generator
└── tests/
    ├── example-content/     # Sample content directory
    └── example-keys/        # Generated TLS certificates
```

---

## Future Considerations (Not in v0.1)

- Pubkey identity for content signing
- EPUB profile restrictions for lighter client rendering
- Compressed navigation indices or embedded manifests
- Simple form submission model (e.g., key-value pairs embedded in headers or metadata)
  - Mechanism for requesting user input via headers or declarative markup
  - Stateless form-like interactions without scripting or cookie-based sessions

---

## Philosophy

Litepub is not a successor to the web. It is a parallel space, focused on:

- Digital permanence
- Low-bandwidth usage
- Offline readability
- Content sovereignty

---

## Appendix: Sample Request/Response

### Request

```
GET /articles/intro.epub HTTP/1.1
Host: leafbook.site
```

### Response

```
HTTP/1.1 200 OK
Content-Type: application/epub+zip
Content-Length: 67890

(binary data...)
```
## License

This project is licensed under the [GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.html).
You may use it in closed-source or commercial projects as long as the terms of the license are followed.