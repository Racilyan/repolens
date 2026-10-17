# 🔎 RepoLens

**Understand any codebase in 10 seconds.** Summarize a repo, generate a README, or explain a file, straight from your terminal.

[![CI](https://github.com/Racilyan/repolens/actions/workflows/ci.yml/badge.svg)](https://github.com/Racilyan/repolens/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

<!-- Add a demo GIF here, it is the single most important thing for a README:
![demo](docs/demo.gif)
-->

```bash
repolens summarize .        # what is this project?
repolens readme . -o README.md   # write me a README
repolens explain src/app.py --level beginner   # what does this file do?
```

## Why RepoLens?

- **Zero dependencies.** Pure Python standard library. One install, nothing else to break.
- **Works with Claude or fully local.** Use the Anthropic API, or run free and offline with [Ollama](https://ollama.com).
- **Safe by default.** `.env` files, keys, certificates, binaries, lock files and anything in `.gitignore` are never sent. Use `--dry-run` to see exactly what would leave your machine.
- **Any language.** `--lang French` (or Arabic, Spanish, ...) and the answer comes back in your language.

## Install

```bash
pipx install git+https://github.com/Racilyan/repolens
# or: pip install git+https://github.com/Racilyan/repolens
```

## Quick start

```bash
export ANTHROPIC_API_KEY=sk-ant-...

repolens summarize .
repolens summarize ~/code/some-project --lang French
repolens readme . -o README.md          # refuses to overwrite unless you add --force
repolens explain main.py --level expert
```

### 100% local and free with Ollama

```bash
ollama pull llama3.1
repolens summarize . --provider ollama
```

### See what gets sent before sending it

```bash
repolens summarize . --dry-run
```

## Options

| Option | Description |
|---|---|
| `--provider anthropic\|ollama` | Which LLM backend to use (default: `anthropic`) |
| `--model NAME` | Model name (default: `claude-sonnet-5-5` / `llama3.1`) |
| `--lang LANGUAGE` | Language of the answer (default: English) |
| `--max-chars N` | Cap on characters sent to the model (default: 60000) |
| `--dry-run` | Print the files that would be sent, call nothing |
| `--level beginner\|intermediate\|expert` | Depth of `explain` |

Environment variables: `ANTHROPIC_API_KEY`, `REPOLENS_PROVIDER`, `REPOLENS_MODEL`, `OLLAMA_HOST`.

## How it works

1. Lists your files (via `git ls-files`, so `.gitignore` is respected) and drops binaries, secrets and noise.
2. Puts the most informative files first (README, manifests, entry points) and fills a character budget.
3. Sends a focused prompt to the model and prints the answer. Prompts live in [`repolens/prompts.py`](repolens/prompts.py), tweak them freely.

## Roadmap

- [ ] `repolens review` — quick code review of a diff
- [ ] `repolens commit` — suggest a commit message from staged changes
- [ ] Streaming output
- [ ] More providers (OpenAI-compatible endpoints)
- [ ] Publish on PyPI

Ideas and PRs are welcome. Open an issue to discuss before big changes.

## Development

```bash
git clone https://github.com/Racilyan/repolens
cd repolens
pip install -e ".[dev]"
pytest
```

## License

MIT
