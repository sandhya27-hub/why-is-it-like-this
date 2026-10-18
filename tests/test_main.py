from pathlib import Path

from fastapi.testclient import TestClient
from git import Repo

from main import app


client = TestClient(app)


def create_repository(path: Path) -> Repo:
    repository = Repo.init(path)
    with repository.config_writer() as config:
        config.set_value("user", "name", "Test Author")
        config.set_value("user", "email", "test@example.com")
    return repository


def commit_file(repository: Repo, name: str, content: str, message: str) -> None:
    file_path = Path(repository.working_tree_dir) / name
    file_path.write_text(content, encoding="utf-8")
    repository.index.add([name])
    repository.index.commit(message)


def test_returns_real_commit_history(tmp_path, monkeypatch):
    repository_path = tmp_path / "repository"
    repository = create_repository(repository_path)
    commit_file(repository, "README.md", "first\n", "Initial commit")
    commit_file(repository, "app.py", "print('hello')\n", "Add app")
    monkeypatch.setenv("ALLOWED_REPOSITORIES", str(tmp_path))

    response = client.post(
        "/commits", json={"repo_path": str(repository_path), "limit": 1}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == str(repository_path.resolve())
    assert len(payload["commits"]) == 1
    commit = payload["commits"][0]
    assert commit["hash"] == repository.head.commit.hexsha
    assert commit["message"] == "Add app"
    assert commit["author_name"] == "Test Author"
    assert commit["author_email"] == "test@example.com"
    assert commit["date"] == repository.head.commit.committed_datetime.isoformat()
    assert commit["changed_files"] == ["app.py"]


def test_rejects_invalid_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOWED_REPOSITORIES", str(tmp_path))

    response = client.post(
        "/commits", json={"repo_path": str(tmp_path), "limit": 201}
    )

    assert response.status_code == 422


def test_rejects_missing_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOWED_REPOSITORIES", str(tmp_path))

    response = client.post(
        "/commits", json={"repo_path": str(tmp_path / "missing")}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Repository path does not exist"


def test_rejects_non_git_directory(tmp_path, monkeypatch):
    non_git_path = tmp_path / "not-a-repository"
    non_git_path.mkdir()
    monkeypatch.setenv("ALLOWED_REPOSITORIES", str(tmp_path))

    response = client.post("/commits", json={"repo_path": str(non_git_path)})

    assert response.status_code == 400
    assert response.json()["detail"] == "Path is not a Git repository"


def test_rejects_path_outside_allowlist(tmp_path, monkeypatch):
    repository_path = tmp_path / "repository"
    create_repository(repository_path)
    allowed_path = tmp_path / "allowed"
    allowed_path.mkdir()
    monkeypatch.setenv("ALLOWED_REPOSITORIES", str(allowed_path))

    response = client.post("/commits", json={"repo_path": str(repository_path)})

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Repository path is outside the configured allowed directories"
    )