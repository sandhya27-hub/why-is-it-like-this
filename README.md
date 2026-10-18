# Why Is It Like This?

This project exposes real Git commit history through a small FastAPI service.
It currently focuses only on retrieving commits; explanations, databases, and
AI processing are intentionally out of scope for this milestone.

## Install

From the project root, create and activate a virtual environment in the VS Code
terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configure allowed repositories

Set `ALLOWED_REPOSITORIES` to one or more existing directories. Separate
multiple directories with the platform path separator (`:` on Linux/macOS).
The endpoint accepts repositories at those directories or below them.

```bash
export ALLOWED_REPOSITORIES="$HOME/Projects"
```

The service fails closed when no valid allowed directory is configured, and
rejects paths outside the configured directories.

## Run the server

```bash
source .venv/bin/activate
export ALLOWED_REPOSITORIES="$HOME/Projects"
uvicorn main:app --reload
```

In another VS Code terminal, request up to 50 commits by default:

```bash
curl -X POST http://127.0.0.1:8000/commits \
	-H 'Content-Type: application/json' \
	-d '{"repo_path":"/absolute/path/to/a/git/repository","limit":20}'
```

The `limit` must be between 1 and 200. Each result contains the commit hash,
message, author name and email, committed date, and changed file paths.
Interactive API documentation is available at
<http://127.0.0.1:8000/docs>.

## Run tests

With the virtual environment activated:

```bash
python -m pytest
```

The tests create temporary local Git repositories with GitPython, so they do
not require internet access or any external repository.