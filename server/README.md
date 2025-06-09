# Litepub Server Implementation

A Python-based reference server implementation of the Litepub protocol (v0.1 Draft).

## Overview

This server converts HTML/XHTML content to EPUB format on-the-fly, implementing the Litepub protocol specification. It serves content over HTTPS with self-signed certificates and supports basic authentication for protected content.

## Features

- **TLS-encrypted connections** (TLS 1.2+) with self-signed certificate support
- **Dynamic EPUB generation** from XHTML/HTML content with automatic asset embedding
- **HTML sanitization** removes scripts, ads, navigation, and other non-content elements
- **Asset bundling** automatically embeds referenced images, CSS, and other resources
- **Directory browsing** with automatic EPUB conversion links
- **Basic authentication** via `.auth` files for protected content
- **Path traversal protection** prevents access outside the content directory
- **Content extraction** intelligently identifies main content from HTML pages
- **TOFU (Trust On First Use)** certificate model for enhanced privacy

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Generate self-signed TLS certificates:
```bash
python server/generate_cert.py
```

This creates certificates in `tests/example-keys/`:
- `server.crt` - TLS certificate
- `server.key` - Private key

## Usage

### Basic Usage

Start the server with default settings:
```bash
python server/server.py
```

The server will:
- Listen on `https://127.0.0.1:8181`
- Serve content from `tests/example-content/`
- Use certificates from `tests/example-keys/`

### Server Configuration

The server can be configured by modifying the `LitepubServer` dataclass parameters:

```python
server = LitepubServer(
    host="127.0.0.1",              # Bind address
    port=8181,                     # Port number  
    cert_path="tests/example-keys/server.crt",  # TLS certificate
    key_path="tests/example-keys/server.key",   # Private key
    content_dir="tests/example-content"         # Content directory
)
```

### Content Structure

#### File Organization
- Place XHTML/HTML files in your content directory (`tests/example-content/` by default)
- Reference assets (images, CSS, fonts) should be accessible relative to the XHTML files
- Directory browsing is supported with automatic index file detection

#### Supported Index Files
When accessing a directory, the server looks for these files in order:
- `index.xhtml`
- `index.html` 
- `index.htm`

#### Authentication
For protected content, create a `.auth` file in the same directory as your content:
```
username:password
```

The server will require HTTP Basic authentication for any content in directories containing `.auth` files.

### Content Processing

#### HTML to XHTML Conversion
The server automatically converts HTML files to clean XHTML by:
1. Parsing the HTML with BeautifulSoup
2. Removing unwanted elements (scripts, ads, navigation, footers, iframes)
3. Extracting main content from `<main>`, `<article>`, or content divs
4. Creating clean XHTML with embedded CSS
5. Caching the converted XHTML file (regenerated when source changes)

#### EPUB Generation
For each request, the server:
1. Parses the XHTML content
2. Identifies and embeds referenced assets (images, CSS, etc.)
3. Creates a valid EPUB 3.2 package with:
   - `mimetype` file
   - `META-INF/container.xml`
   - `content.opf` manifest
   - `OEBPS/content.xhtml` main content
   - Embedded assets in `OEBPS/` directory

#### URL Mapping
- `/path/to/file.html` → serves as EPUB after HTML→XHTML conversion
- `/path/to/file.xhtml` → serves as EPUB directly
- `/path/to/file.epub` → maps to `/path/to/file.xhtml` and serves as EPUB
- `/directory/` → looks for index files and serves directory listing if none found

## Implementation Details

### Dependencies
- **aiohttp** (≥3.9.5) - Async HTTP server framework
- **beautifulsoup4** (≥4.12.3) - HTML parsing and content extraction
- **lxml** (≥5.2.1) - XML/XHTML processing for EPUB generation

### Architecture
The server is implemented as an async Python application using:
- `LitepubServer` dataclass for configuration and request handling
- Path traversal protection via `pathlib.Path.resolve()`
- Asset embedding with MIME type detection
- EPUB packaging using Python's `zipfile` module
- TLS handling with Python's built-in `ssl` module

### Security Features
- **Path traversal protection**: All file access is restricted to the configured content directory
- **TLS encryption**: All connections require HTTPS with TLS 1.2+
- **Self-signed certificates**: No CA verification required (TOFU model)
- **Basic authentication**: Simple username/password protection via `.auth` files
- **Content sanitization**: Automatic removal of scripts and potentially harmful content

## Development

### Running Tests
The server includes example content in `tests/example-content/` for testing and development.

### Debugging
The server logs errors to the console and includes stack traces for debugging. All exceptions during EPUB generation result in HTTP 500 responses with error details.

### Extending the Server
The modular design allows easy extension:
- Add new content processors by extending the HTML→XHTML conversion
- Implement additional authentication methods in `_check_basic_auth()`
- Add new response formats alongside EPUB generation
- Customize EPUB metadata in `_create_content_opf()`

## Security Notes

- **TLS is required**: All connections must be encrypted
- **Self-signed certificates**: Clients should implement TOFU certificate validation
- **Basic auth over TLS**: Authentication credentials are only secure over encrypted connections
- **Content directory isolation**: The server cannot access files outside the configured content directory
- **No script execution**: All JavaScript and dynamic content is stripped from HTML

## License

                   GNU LESSER GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.


  This version of the GNU Lesser General Public License incorporates
the terms and conditions of version 3 of the GNU General Public
License, supplemented by the additional permissions listed below.

  0. Additional Definitions.

  As used herein, "this License" refers to version 3 of the GNU Lesser
General Public License, and the "GNU GPL" refers to version 3 of the GNU
General Public License.

  "The Library" refers to a covered work governed by this License,
other than an Application or a Combined Work as defined below.

  An "Application" is any work that makes use of an interface provided
by the Library, but which is not otherwise based on the Library.
Defining a subclass of a class defined by the Library is deemed a mode
of using an interface provided by the Library.

  A "Combined Work" is a work produced by combining or linking an
Application with the Library.  The particular version of the Library
with which the Combined Work was made is also called the "Linked
Version".

  The "Minimal Corresponding Source" for a Combined Work means the
Corresponding Source for the Combined Work, excluding any source code
for portions of the Combined Work that, considered in isolation, are
based on the Application, and not on the Linked Version.

  The "Corresponding Application Code" for a Combined Work means the
object code and/or source code for the Application, including any data
and utility programs needed for reproducing the Combined Work from the
Application, but excluding the System Libraries of the Combined Work.

  1. Exception to Section 3 of the GNU GPL.

  You may convey a covered work under sections 3 and 4 of this License
without being bound by section 3 of the GNU GPL.

  2. Conveying Modified Versions.

  If you modify a copy of the Library, and, in your modifications, a
facility refers to a function or data to be supplied by an Application
that uses the facility (other than as an argument passed when the
facility is invoked), then you may convey a copy of the modified
version:

   a) under this License, provided that you make a good faith effort to
   ensure that, in the event an Application does not supply the
   function or data, the facility still operates, and performs
   whatever part of its purpose remains meaningful, or

   b) under the GNU GPL, with none of the additional permissions of
   this License applicable to that copy.

  3. Object Code Incorporating Material from Library Header Files.

  The object code form of an Application may incorporate material from
a header file that is part of the Library.  You may convey such object
code under terms of your choice, provided that, if the incorporated
material is not limited to numerical parameters, data structure
layouts and accessors, or small macros, inline functions and templates
(ten or fewer lines in length), you do both of the following:

   a) Give prominent notice with each copy of the object code that the
   Library is used in it and that the Library and its use are
   covered by this License.

   b) Accompany the object code with a copy of the GNU GPL and this license
   document.

  4. Combined Works.

  You may convey a Combined Work under terms of your choice that,
taken together, effectively do not restrict modification of the
portions of the Library contained in the Combined Work and reverse
engineering for debugging such modifications, if you also do each of
the following:

   a) Give prominent notice with each copy of the Combined Work that
   the Library is used in it and that the Library and its use are
   covered by this License.

   b) Accompany the Combined Work with a copy of the GNU GPL and this license
   document.

   c) For a Combined Work that displays copyright notices during
   execution, include the copyright notice for the Library among
   these notices, as well as a reference directing the user to the
   copies of the GNU GPL and this license document.

   d) Do one of the following:

       0) Convey the Minimal Corresponding Source under the terms of this
       License, and the Corresponding Application Code in a form
       suitable for, and under terms that permit, the user to
       recombine or relink the Application with a modified version of
       the Linked Version to produce a modified Combined Work, in the
       manner specified by section 6 of the GNU GPL for conveying
       Corresponding Source.

       1) Use a suitable shared library mechanism for linking with the
       Library.  A suitable mechanism is one that (a) uses at run time
       a copy of the Library already present on the user's computer
       system, and (b) will operate properly with a modified version
       of the Library that is interface-compatible with the Linked
       Version.

   e) Provide Installation Information, but only if you would otherwise
   be required to provide such information under section 6 of the
   GNU GPL, and only to the extent that such information is
   necessary to install and execute a modified version of the
   Combined Work produced by recombining or relinking the
   Application with a modified version of the Linked Version. (If
   you use option 4d0, the Installation Information must accompany
   the Minimal Corresponding Source and Corresponding Application
   Code. If you use option 4d1, you must provide the Installation
   Information in the manner specified by section 6 of the GNU GPL
   for conveying Corresponding Source.)

  5. Combined Libraries.

  You may place library facilities that are a work based on the
Library side by side in a single library together with other library
facilities that are not Applications and are not covered by this
License, and convey such a combined library under terms of your
choice, if you do both of the following:

   a) Accompany the combined library with a copy of the same work based
   on the Library, uncombined with any other library facilities,
   conveyed under the terms of this License.

   b) Give prominent notice with the combined library that part of it
   is a work based on the Library, and explaining where to find the
   accompanying uncombined form of the same work.

  6. Revised Versions of the GNU Lesser General Public License.

  The Free Software Foundation may publish revised and/or new versions
of the GNU Lesser General Public License from time to time. Such new
versions will be similar in spirit to the present version, but may
differ in detail to address new problems or concerns.

  Each version is given a distinguishing version number. If the
Library as you received it specifies that a certain numbered version
of the GNU Lesser General Public License "or any later version"
applies to it, you have the option of following the terms and
conditions either of that published version or of any later version
published by the Free Software Foundation. If the Library as you
received it does not specify a version number of the GNU Lesser
General Public License, you may choose any version of the GNU Lesser
General Public License ever published by the Free Software Foundation.

  If the Library as you received it specifies that a proxy can decide
whether future versions of the GNU Lesser General Public License shall
apply, that proxy's public statement of acceptance of any version is
permanent authorization for you to choose that version for the
Library.
