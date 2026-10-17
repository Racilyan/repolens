from pathlib import Path

from repolens.cli import main
from repolens.collector import collect, collect_file


def make_repo(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text("# Demo\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("nope")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\0\0")
    (tmp_path / "data.dat").write_bytes(b"abc\0def")
    (tmp_path / ".env").write_text("SECRET=1")
    (tmp_path / "server.pem").write_text("-----BEGIN-----")
    return tmp_path


def test_collect_skips_binaries_secrets_and_ignored_dirs(tmp_path):
    snap = collect(make_repo(tmp_path))
    included = [rel for rel, _ in snap.files]
    assert included == ["README.md", "src/app.py"]  # README comes first
    assert ".env" not in snap.paths and "server.pem" not in snap.paths


def test_collect_respects_budget(tmp_path):
    (tmp_path / "big.txt").write_text("x" * 5000)
    snap = collect(tmp_path, max_chars=1000)
    assert snap.chars <= 1000


def test_collect_file_rejects_binary(tmp_path):
    binary = tmp_path / "a.dat"
    binary.write_bytes(b"\0\0\0")
    try:
        collect_file(binary)
    except OSError:
        return
    raise AssertionError("expected OSError")


def test_dry_run_prints_files(tmp_path, capsys):
    repo = make_repo(tmp_path)
    assert main(["summarize", str(repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "  README.md" in out and "  .env " not in out and "server.pem" not in out


def test_readme_refuses_to_overwrite(tmp_path):
    repo = make_repo(tmp_path)
    assert main(["readme", str(repo), "-o", str(repo / "README.md")]) == 1
