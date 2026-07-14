---
name: wsl_docker_fallback
description: Guide and cheatsheet on running Docker commands in WSL 2 by using the host's Windows docker.exe client as a fallback.
---

# WSL 2 Docker Client Fallback Guide

When developer distros do not have Docker Desktop integration turned on, standard Linux docker commands will fail. Follow these patterns to fallback to host CLI operations:

## Commands Fallback Cheatsheet

Always substitute standard docker command prefixes with `.exe` extensions:

* **Checking Status:**
  ```bash
  docker.exe ps
  ```
* **Spinning up Compose services:**
  ```bash
  docker.exe compose up db -d
  ```
* **Stopping services:**
  ```bash
  docker.exe compose down
  ```

* **Direct Database Operations (Bypassing Python table locks):**
  If Python `drop_all` scripts hang indefinitely due to open connection locks, force the drop directly inside the running container:
  ```bash
  docker.exe exec -i packvote-db-1 psql -U user -d packvote -c "DROP TABLE IF EXISTS destinations CASCADE;"
  ```

## Active Google Gemini Embedding Specifications
When using Google Gemini for text embeddings in developer environments:
* **Preferred Model:** `models/gemini-embedding-001` (GA)
* **Dimension Size:** `3072` (Ensure this is set as `EMBEDDING_DIMENSION` in `.env`)
* Note: `models/embedding-001` and `models/text-embedding-004` are deprecated/unsupported on developer endpoints and will throw 404 errors.

## Persistent Database Testing Isolation Rule
When executing test suites that write to a persistent local Docker database, always use random identifiers (like UUIDs) for keys, emails, and identifiers in test mocks to prevent collisions with residual data from previous test runs.

