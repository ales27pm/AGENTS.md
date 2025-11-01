#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

readonly PROVIDED_ROOT="${1:-$(pwd)}"
readonly OUTPUT_TARGET="${GITHUB_OUTPUT:-/dev/stdout}"

log() {
  printf '[autodetect] %s\n' "$*" >&2
}

if [[ ! -d "$PROVIDED_ROOT" ]]; then
  log "error: repository root '$PROVIDED_ROOT' not found"
  exit 1
fi

readonly REPO_ROOT="$(cd "$PROVIDED_ROOT" && pwd)"

set_output() {
  printf '%s=%s\n' "$1" "$2" >>"$OUTPUT_TARGET"
}

STACK="unknown"
INSTALL_CMD=":"
LINT_CMD=":"
TYPECHECK_CMD=":"
TEST_CMD=":"

has_file() {
  test -f "$REPO_ROOT/$1"
}

has_dir() {
  test -d "$REPO_ROOT/$1"
}

set_stack() {
  STACK="$1"
  INSTALL_CMD="$2"
  LINT_CMD="$3"
  TYPECHECK_CMD="$4"
  TEST_CMD="$5"
}

detect_node_manager() {
  if has_file "pnpm-lock.yaml" || has_file "pnpm-workspace.yaml"; then
    echo pnpm
    return
  fi

  if has_file "package-lock.json" || has_file "npm-shrinkwrap.json"; then
    echo npm
    return
  fi

  if has_file "yarn.lock"; then
    if has_file ".yarnrc.yml" || has_dir ".yarn"; then
      echo yarn-modern
    else
      echo yarn
    fi
    return
  fi

  if has_file "bun.lockb"; then
    echo bun
    return
  fi

  if has_file "package.json"; then
    local pm
    pm=$(grep -E '"packageManager"\s*:\s*"' "$REPO_ROOT/package.json" 2>/dev/null | head -n1 | sed -E 's/.*"packageManager"\s*:\s*"([^"]+)".*/\1/' || true)
    case "$pm" in
      pnpm@*) echo pnpm; return ;;
      yarn@*) echo yarn-modern; return ;;
      npm@*) echo npm; return ;;
      bun@*) echo bun; return ;;
      *) : ;;
    esac
  fi

  echo npm
}

detect_deno() {
  if has_file "deno.json" || has_file "deno.jsonc"; then
    set_stack \
      "deno" \
      "deno cache" \
      "deno task lint || deno lint" \
      "deno task check || deno check" \
      "deno task test || deno test"
    return 0
  fi
  return 1
}

detect_bun() {
  if has_file "bun.lockb" && has_file "package.json"; then
    set_stack \
      "bun" \
      "bun install --frozen-lockfile" \
      "bun run lint || bunx eslint ." \
      "bun run typecheck || bunx tsc -p ." \
      "bun test"
    return 0
  fi
  return 1
}

detect_node() {
  if has_file "package.json"; then
    local manager
    manager=$(detect_node_manager)
    case "$manager" in
      pnpm)
        set_stack \
          "node" \
          "pnpm install --frozen-lockfile" \
          "pnpm lint || pnpm exec eslint ." \
          "pnpm typecheck || pnpm exec tsc -p ." \
          "pnpm test -- --runInBand"
        ;;
      yarn)
        set_stack \
          "node" \
          "yarn install --frozen-lockfile" \
          "yarn lint || npx eslint ." \
          "yarn typecheck || npx tsc -p ." \
          "yarn test --watch=false"
        ;;
      yarn-modern)
        set_stack \
          "node" \
          "yarn install --immutable" \
          "yarn lint || yarn dlx eslint ." \
          "yarn typecheck || yarn dlx tsc -p ." \
          "yarn test --runInBand"
        ;;
      bun)
        set_stack \
          "node" \
          "bun install --frozen-lockfile" \
          "bun run lint || bunx eslint ." \
          "bun run typecheck || bunx tsc -p ." \
          "bun test"
        ;;
      *)
        set_stack \
          "node" \
          "npm ci" \
          "npm run lint --if-present || npx eslint ." \
          "npm run typecheck --if-present || npx tsc -p ." \
          "npm test --silent"
        ;;
    esac
    return 0
  fi
  return 1
}

detect_python() {
  if has_file "pyproject.toml" || has_file "requirements.txt" || has_file "pdm.lock" || has_file "uv.lock" || has_file "poetry.lock"; then
    if has_file "uv.lock"; then
      set_stack \
        "python" \
        "uv sync --all-extras --dev || pip install -e '.[dev]'" \
        "uv run ruff check . || ruff check ." \
        "uv run mypy --strict || mypy --strict" \
        "uv run pytest -q --maxfail=1 --disable-warnings || pytest -q --maxfail=1 --disable-warnings"
    elif has_file "pdm.lock"; then
      set_stack \
        "python" \
        "pdm install --no-self || pip install -e '.[dev]'" \
        "pdm run ruff check . || ruff check ." \
        "pdm run mypy --strict || mypy --strict" \
        "pdm run pytest -q --maxfail=1 --disable-warnings || pytest -q --maxfail=1 --disable-warnings"
    elif has_file "poetry.lock"; then
      set_stack \
        "python" \
        "poetry install --no-root || pip install -e '.[dev]'" \
        "poetry run ruff check . || ruff check ." \
        "poetry run mypy --strict || mypy --strict" \
        "poetry run pytest -q --maxfail=1 --disable-warnings || pytest -q --maxfail=1 --disable-warnings"
    else
      set_stack \
        "python" \
        "pip install -e '.[dev]' || pip install -r requirements.txt" \
        "ruff check . || flake8" \
        "mypy --strict || pyright" \
        "pytest -q --maxfail=1 --disable-warnings"
    fi
    return 0
  fi
  return 1
}

detect_go() {
  if has_file "go.mod"; then
    set_stack \
      "go" \
      "go mod download" \
      "golangci-lint run || gofmt -l ." \
      "go vet ./..." \
      "go test ./... -count=1"
    return 0
  fi
  return 1
}

detect_rust() {
  if has_file "Cargo.toml"; then
    set_stack \
      "rust" \
      "cargo fetch" \
      "cargo fmt --all -- --check" \
      "cargo clippy --all-targets --all-features -- -D warnings" \
      "cargo test --all --locked"
    return 0
  fi
  return 1
}

detect_elixir() {
  if has_file "mix.exs"; then
    set_stack \
      "elixir" \
      "mix deps.get" \
      "mix format --check-formatted" \
      ":" \
      "mix test"
    return 0
  fi
  return 1
}

detect_php() {
  if has_file "composer.json"; then
    set_stack \
      "php" \
      "composer install --no-interaction --prefer-dist" \
      "composer run lint || vendor/bin/phpcs || true" \
      "composer run stan || vendor/bin/phpstan analyse || true" \
      "composer test || vendor/bin/phpunit || true"
    return 0
  fi
  return 1
}

detect_ruby() {
  if has_file "Gemfile"; then
    set_stack \
      "ruby" \
      "bundle install --jobs=4 --retry=3" \
      "bundle exec rubocop || rubocop" \
      ":" \
      "bundle exec rake test || bundle exec rspec || true"
    return 0
  fi
  return 1
}

detect_cmake() {
  if has_file "CMakeLists.txt"; then
    set_stack \
      "cmake" \
      ":" \
      ":" \
      ":" \
      "ctest --output-on-failure || true"
    return 0
  fi
  return 1
}

detect_android() {
  if has_dir "android" && has_file "android/gradlew"; then
    set_stack \
      "android" \
      "./android/gradlew dependencies" \
      "./android/gradlew lint" \
      ":" \
      "./android/gradlew test"
    return 0
  fi
  return 1
}

run_detectors() {
  local detectors=(
    detect_deno
    detect_bun
    detect_node
    detect_python
    detect_go
    detect_rust
    detect_elixir
    detect_php
    detect_ruby
    detect_cmake
    detect_android
  )

  for detector in "${detectors[@]}"; do
    if "$detector"; then
      return 0
    fi
  done
  return 1
}

run_detectors || true

log "stack=$STACK"
log "install=$INSTALL_CMD"
log "lint=$LINT_CMD"
log "typecheck=$TYPECHECK_CMD"
log "test=$TEST_CMD"

set_output stack "$STACK"
set_output install "$INSTALL_CMD"
set_output lint "$LINT_CMD"
set_output typecheck "$TYPECHECK_CMD"
set_output test "$TEST_CMD"
