import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel, Field


MAX_COMMIT_LIMIT = 200


class CommitRequest(BaseModel):
    repo_path: str = Field(min_length=1, max_length=4096)
    limit: int = Field(default=50, ge=1, le=MAX_COMMIT_LIMIT)


class CommitRecord(BaseModel):
    hash: str
    message: str
    author_name: str
    author_email: str
    date: str
    changed_files: list[str]


class CommitResponse(BaseModel):
    repository: str
    commits: list[CommitRecord]


app = FastAPI(title="Why Is It Like This?", version="0.1.0")


def _configured_roots() -> list[Path]:
    configured = os.environ.get("ALLOWED_REPOSITORIES", "")
    roots = []
    for raw_root in configured.split(os.pathsep):
        if not raw_root.strip():
            continue
        root = Path(raw_root).expanduser().resolve()
        if root.is_dir():
            roots.append(root)
    return roots


def _is_allowed(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


@app.post("/commits", response_model=CommitResponse)
def get_commits(request: CommitRequest) -> CommitResponse:
    repository_path = Path(request.repo_path).expanduser().resolve()
    allowed_roots = _configured_roots()

    if not allowed_roots:
        raise HTTPException(
            status_code=500,
            detail="No valid repository directories are configured",
        )
    if not _is_allowed(repository_path, allowed_roots):
        raise HTTPException(
            status_code=403,
            detail="Repository path is outside the configured allowed directories",
        )
    if not repository_path.exists():
        raise HTTPException(status_code=404, detail="Repository path does not exist")
    if not repository_path.is_dir():
        raise HTTPException(status_code=400, detail="Repository path must be a directory")

    try:
        repository = Repo(repository_path, search_parent_directories=False)
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise HTTPException(status_code=400, detail="Path is not a Git repository")

    records = []
    for commit in repository.iter_commits(max_count=request.limit):
        records.append(
            CommitRecord(
                hash=commit.hexsha,
                message=commit.message.rstrip("\n"),
                author_name=commit.author.name,
                author_email=commit.author.email,
                date=commit.committed_datetime.isoformat(),
                changed_files=list(commit.stats.files.keys()),
            )
        )

    return CommitResponse(repository=str(repository_path), commits=records)