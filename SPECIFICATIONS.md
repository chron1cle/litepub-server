# 📐 Litepub Standards Specification (v0.1 Draft)

## ✨ Purpose

This document defines behavioral standards and best practices for Litepub implementations, ensuring privacy, compatibility, and user-first design across the Lite Web ecosystem. These standards supplement the protocol spec by covering conventions around content formatting, input handling, and ethical safeguards.

---

## 📜 Core Standards

### 1. 📦 Self-Contained Content

* All Litepub content **must be served as complete EPUB files**.
* All resources (images, fonts, styles) **must be embedded**; no external fetches.
* Pages **must be readable offline** and renderable without network dependency.

### 2. 🔒 Encrypted by Default

* All Litepub connections must use TLS.
* Self-signed certificates are accepted under a TOFU (Trust On First Use) model.
* Clients must validate and store server fingerprints, prompting users on change.

### 3. 🧠 Stateless by Design

* No cookies, sessions, or local storage allowed.
* Every interaction must be handled via clean, stateless requests.

---

## 📩 Input and Dynamic Content

### 4. 🔍 Query Isolation and Form Declaration

* **All query parameters must be stripped from links inside Litepub content.**
* Clients must **only allow GET queries** to be submitted via a user-driven form prompt.
* Links that trigger user input must use a special attribute, for example:

  ```xml
  <a href="/search" rel="litepub:form" data-fields="q:Search term">
    Search the Archive
  </a>
  ```
* The browser must handle prompting the user for values, building the query string, and submitting the request.

### 5. 📄 Server Fallbacks

* When a query is missing or incomplete, servers must respond gracefully.
* Valid fallback responses include:

  * A basic instructional page
  * A generic list of content
  * A link back to the form intent
* **Errors or 4xx responses should not be shown to standard EPUB readers** when accessed without parameters.

### 6. 🛡️ Anti-Exploitation Safeguards

* No tracking IDs, session tokens, or referrer strings may be embedded in content links.
* All dynamic content must be:

  * Transparent (clearly reflects user input)
  * Predictable (does not change silently)
  * Inspectable (stored as visible EPUB content, not hidden logic)

---

## 🧪 Client Behavior Requirements

### 7. 🎛️ User-First Input

* Clients must style and render form prompts independently of content.
* Form intent links (i.e., those with `rel="litepub:form"`) must be clearly distinguished from regular navigation links.
* Clients should render them using UI elements such as buttons or icons that visually indicate the user will be prompted for input.
* Form actions must never be a surprise — the user must clearly understand they are about to enter information before the request is sent.
* Input should be accessible, minimal, and styled according to user preferences.

### 8. 🧹 Content Hygiene

* Query-bearing links must be stripped from rendered content.
* Clients must ignore and remove all query parameters found in `<a href>` attributes within EPUB content.
* All user input must come only from Litepub-declared form prompts or manual entry, never embedded link data.
* EPUB content must be clean, valid, and conform to Litepub’s subset profile.

### 9. 🪞 Transparency by Default

* Clients should allow users to inspect:

  * Submitted query strings
  * Link targets
  * The original `.epub` structure if desired

---

## 🚧 Notes for Future Revisions

* A formal Litepub XHTML Profile (defining allowed tags and attributes)
* A `litepub.json` manifest for site-level metadata
* Identity and pubkey trust handling
* Directory auto-indexing behavior
* Federated search and result interoperability

---

This spec exists to protect user agency, preserve privacy, and ensure consistency in the growing Lite Web ecosystem. Let the tools serve the people — not the other way around.
