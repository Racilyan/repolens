"""Command-line interface: repolens summarize | readme | explain."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, prompts
from .collector import Snapshot, collect, collect_file
from .llm import LLMError, complete, resolve


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--provider", choices=["anthropic", "ollama"], help="LLM provider")
    common.add_argument("--model", help="model name (default depends on provider)")
    common.add_argument("--lang", default="English", help="language of the answer (default: English)")
    common.add_argument("--max-chars", type=int, default=60_000, help="max characters sent to the LLM")
    common.add_argument("--dry-run", action="store_true",
                        help="show exactly what would be sent, without calling any API")

    parser = argparse.ArgumentParser(
        prog="repolens", description="Understand any codebase in seconds, from your terminal.")
    parser.add_argument("--version", action="version", version=f"repolens {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("summarize", parents=[common], help="summarize a repository")
    s.add_argument("path", nargs="?", default=".", help="repository folder (default: .)")

    r = sub.add_parser("readme", parents=[common], help="generate a README.md")
    r.add_argument("path", nargs="?", default=".", help="repository folder (default: .)")
    r.add_argument("-o", "--output", help="write to this file instead of stdout")
    r.add_argument("--force", action="store_true", help="overwrite the output file if it exists")

    e = sub.add_parser("explain", parents=[common], help="explain a source file")
    e.add_argument("file", help="file to explain")
    e.add_argument("--level", choices=["beginner", "intermediate", "expert"], default="intermediate")
    return parser


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _dry_run(snapshot: Snapshot) -> None:
    print(f"Files that would be sent ({len(snapshot.files)}), "
          f"~{snapshot.chars:,} characters (~{snapshot.chars // 4:,} tokens):")
    for rel, content in snapshot.files:
        print(f"  {rel}  ({len(content):,} chars)")
    if snapshot.skipped:
        print(f"{snapshot.skipped} more file(s) skipped to stay within --max-chars.")
    print("Never sent: .env files, keys/certificates, binaries, lock files, .gitignore'd files.")


def run(args: argparse.Namespace) -> int:
    if args.command == "explain":
        target = Path(args.file)
        if not target.is_file():
            raise OSError(f"{target} is not a file")
        snapshot = collect_file(target, args.max_chars)
        system, max_tokens = prompts.explain(args.level, args.lang), 2000
    else:
        root = Path(args.path)
        if not root.is_dir():
            raise OSError(f"{root} is not a folder")
        if args.command == "readme" and args.output:
            out = Path(args.output)
            if out.exists() and not args.force:
                raise OSError(f"{out} already exists (use --force to overwrite)")
        snapshot = collect(root, args.max_chars)
        if args.command == "summarize":
            system, max_tokens = prompts.summarize(args.lang), 1200
        else:
            system, max_tokens = prompts.readme(args.lang), 3000

    if args.dry_run:
        _dry_run(snapshot)
        return 0

    provider, model = resolve(args.provider, args.model)
    print(f"repolens: asking {provider}/{model} ...", file=sys.stderr)
    text = _strip_fence(complete(system, snapshot.render(), provider, model, max_tokens))

    if args.command == "readme" and args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (LLMError, OSError) as err:
        print(f"repolens: {err}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
