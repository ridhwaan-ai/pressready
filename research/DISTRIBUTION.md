# Where AI agents discover PressReady

Nothing here is submitted yet. Every listing is public, so each needs the Owner's OK first.
Listing details below are from general knowledge of these registries; re-check each site's current
submission rules before submitting.

## Prerequisites (in order)
1. First PyPI release (Owner OKs, then creates a GitHub release; `publish.yml` does the rest).
2. Gumroad key product live, so the paid tier exists (otherwise the listing promises only the free tier).
3. Repo visibility: Glama, Smithery and awesome-list PRs need a public repo or a public package.
   The repo is PRIVATE now. Options: make it public (Owner decision), or list only the hosted
   service and PyPI package. Flag this to the Owner.

## Targets
| Where | What it needs | Cost |
|---|---|---|
| Official MCP Registry (registry.modelcontextprotocol.io) | `server.json`; PyPI package ownership proved by a line `mcp-name: io.github.ridhwaan-ai/pressready` in the PyPI README; publish with the `mcp-publisher` CLI, GitHub login by the Owner | free |
| PyPI | keywords and readme (added to pyproject); classifiers | free |
| Smithery | GitHub repo plus a `smithery.yaml`, or a hosted URL; Owner signs in | free |
| Glama | auto-indexes public GitHub MCP servers; claim the listing with the Owner's GitHub login | free |
| PulseMCP | submit form with server URL or repo; it also ingests the official registry | free |
| mcp.so | submit form (name, URL, description) | free |
| awesome-mcp-servers lists (punkpeanut, wong2, appcypher) | a PR adding one line in the right category (Other tools / Publishing) | free |

## Draft listing text
Name: PressReady

One line (under 100 characters): Turn Markdown chapters into KDP-ready EPUB, print PDF and wrap cover.

Short description:
PressReady builds the files Amazon KDP asks for from a Markdown manuscript, metadata and a front-cover
image. You get a valid EPUB 3, a print interior PDF (5x8, 5.5x8.5, 6x9 or 8.5x11), a full-wrap paperback
cover PDF with the spine width computed from page count and paper type, and a JSON upload checklist.
It has typed errors that say what to fix, so an agent can run the whole flow without a human.

Tools: build_book, spine_width, list_trim_sizes.
Interfaces: MCP (stdio, `pressready-mcp`), HTTP API with OpenAPI, CLI.
Docs: https://pressready-wp38.onrender.com/llms.txt
Install: `pip install pressready` (after the first release)
Pricing: free tier of 3 builds a day; unlimited with a license key (price to be set by the Owner).
Disclosure: built and maintained by an AI agent under the Owner's supervision. It does not log in to KDP.
Limits: it does not upload to KDP, and it cannot guarantee acceptance. The checklist lists warnings.

Suggested categories/tags: publishing, documents, files, books, productivity.

## server.json draft (official registry)
```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.ridhwaan-ai/pressready",
  "description": "Turn Markdown chapters into KDP-ready EPUB, print interior PDF and wrap cover PDF.",
  "version": "0.1.0",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "pressready",
      "version": "0.1.0",
      "runtimeHint": "uvx",
      "transport": { "type": "stdio" }
    }
  ]
}
```
Check the schema URL and the field names against the current docs before use.

## Order of submission
Official registry, then PyPI keywords. PulseMCP and Glama usually pick those up. Then Smithery, mcp.so,
and one PR per awesome list. Space the PRs out and write each one by hand. No bulk or spam submissions.
