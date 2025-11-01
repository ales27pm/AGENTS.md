#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# shellcheck disable=SC2155
readonly REPO_ROOT="${1:-$(pwd)}"
readonly OUTPUT_TARGET="${GITHUB_OUTPUT:-/dev/stdout}"

log() {
  printf '[autodetect] %s\n' "$*" >&2
}

set_output() {
  printf '%s=%s\n' "$1" "$2" >>"$OUTPUT_TARGET"
}

# Defaults represent a no-op stack.
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
    # Peek at packageManager field without jq; fall back to npm if not found.
    local pm
    pm=$(grep -E '"packageManager"\s*:\s*"' "$REPO_ROOT/package.json" 2>/dev/null | head -n1 | sed -E 's/.*"packageManager"\s*:\s*"([^"]+)".*/\1/' || true)
    case "$pm" in
      pnpm@* ) echo pnpm; return ;;
      yarn@* ) echo yarn-modern; return ;;
      npm@* ) echo npm; return ;;
      bun@* ) echo bun; return ;;
      * ) : ;;
    esac
  fi

  echo npm
}

if has_file "deno.json" || has_file "deno.jsonc"; then
  STACK="deno"
  INSTALL_CMD="deno cache"
  LINT_CMD="deno task lint || deno lint"
  TYPECHECK_CMD="deno task check || deno check"
  TEST_CMD="deno task test || deno test"
elif has_file "bun.lockb" && has_file "package.json"; then
  STACK="bun"
  INSTALL_CMD="bun install --frozen-lockfile"
  LINT_CMD="bun run lint || bunx eslint ."
  TYPECHECK_CMD="bun run typecheck || bunx tsc -p ."
  TEST_CMD="bun test"
elif has_file "package.json"; then
  STACK="node"
  case "$(detect_node_manager)" in
    pnpm)
      INSTALL_CMD="pnpm install --frozen-lockfile"
      LINT_CMD="pnpm lint || pnpm exec eslint ."
      TYPECHECK_CMD="pnpm typecheck || pnpm exec tsc -p ."
      TEST_CMD="pnpm test -- --runInBand"
      ;;
    yarn)
      INSTALL_CMD="yarn install --frozen-lockfile"
      LINT_CMD="yarn lint || npx eslint ."
      TYPECHECK_CMD="yarn typecheck || npx tsc -p ."
      TEST_CMD="yarn test --watch=false"
      ;;
    yarn-modern)
      INSTALL_CMD="yarn install --immutable"
      LINT_CMD="yarn lint || yarn dlx eslint ."
      TYPECHECK_CMD="yarn typecheck || yarn dlx tsc -p ."
      TEST_CMD="yarn test --runInBand"
      ;;
    bun)
      INSTALL_CMD="bun install --frozen-lockfile"
      LINT_CMD="bun run lint || bunx eslint ."
      TYPECHECK_CMD="bun run typecheck || bunx tsc -p ."
      TEST_CMD="bun test"
      ;;
    *)
      INSTALL_CMD="npm ci"
      LINT_CMD="npm run lint --if-present || npx eslint ."
      TYPECHECK_CMD="npm run typecheck --if-present || npx tsc -p ."
      TEST_CMD="npm test --silent"
      ;;
  esac
elif has_file "pyproject.toml" || has_file "requirements.txt" || has_file "pdm.lock" || has_file "uv.lock"; then
  STACK="python"
  if has_file "uv.lock"; then
    INSTALL_CMD="uv sync --all-extras --dev || pip install -e '.[dev]'"
    LINT_CMD="uv run ruff check . || ruff check ."
    TYPECHECK_CMD="uv run mypy --strict || mypy --strict"
    TEST_CMD="uv run pytest -q --maxfail=1 --disable-warnings || pytest -q --maxfail=1 --disable-warnings"
  elif has_file "pdm.lock"; then
    INSTALL_CMD="pdm install --no-self || pip install -e '.[dev]'"
    LINT_CMD="pdm run ruff check . || ruff check ."
    TYPECHECK_CMD="pdm run mypy --strict || mypy --strict"
    TEST_CMD="pdm run pytest -q --maxfail=1 --disable-warnings || pytest -q --maxfail=1 --disable-warnings"
  elif has_file "poetry.lock"; then
    INSTALL_CMD="poetry install --no-root || pip install -e '.[dev]'"
    LINT_CMD="poetry run ruff check . || ruff check ."
    TYPECHECK_CMD="poetry run mypy --strict || mypy --strict"
    TEST_CMD="poetry run pytest -q --maxfail=1 --disable-warnings || pytest -q --maxfail=1 --disable-warnings"
  else
    INSTALL_CMD="pip install -e '.[dev]' || pip install -r requirements.txt"
    LINT_CMD="ruff check . || flake8"
    TYPECHECK_CMD="mypy --strict || pyright"
    TEST_CMD="pytest -q --maxfail=1 --disable-warnings"
  fi
elif has_file "poetry.lock" && has_file "poetry.toml"; then
  STACK="python"
  INSTALL_CMD="poetry install --no-root"
  LINT_CMD="poetry run ruff check ."
  TYPECHECK_CMD="poetry run mypy --strict"
  TEST_CMD="poetry run pytest -q --maxfail=1 --disable-warnings"
elif has_file "go.mod"; then
  STACK="go"
  INSTALL_CMD="go mod download"
  LINT_CMD="golangci-lint run || gofmt -l ."
  TYPECHECK_CMD="go vet ./..."
  TEST_CMD="go test ./... -count=1"
elif has_file "Cargo.toml"; then
  STACK="rust"
  INSTALL_CMD="cargo fetch"
  LINT_CMD="cargo fmt --all -- --check"
  TYPECHECK_CMD="cargo clippy --all-targets --all-features -- -D warnings"
  TEST_CMD="cargo test --all --locked"
elif has_file "mix.exs"; then
  STACK="elixir"
  INSTALL_CMD="mix deps.get"
  LINT_CMD="mix format --check-formatted"
  TYPECHECK_CMD=":"
  TEST_CMD="mix test"
elif has_file "composer.json"; then
  STACK="php"
  INSTALL_CMD="composer install --no-interaction --prefer-dist"
  LINT_CMD="composer run lint || vendor/bin/phpcs || true"
  TYPECHECK_CMD="composer run stan || vendor/bin/phpstan analyse || true"
  TEST_CMD="composer test || vendor/bin/phpunit || true"
elif has_file "Gemfile"; then
  STACK="ruby"
  INSTALL_CMD="bundle install --jobs=4 --retry=3"
  LINT_CMD="bundle exec rubocop || rubocop"
  TYPECHECK_CMD=":"
  TEST_CMD="bundle exec rake test || bundle exec rspec || true"
elif has_file "CMakeLists.txt"; then
  STACK="cmake"
  INSTALL_CMD=":"
  LINT_CMD=":"
  TYPECHECK_CMD=":"
  TEST_CMD="ctest --output-on-failure || true"
elif has_dir "android" && has_file "android/gradlew"; then
  STACK="android"
  INSTALL_CMD="./android/gradlew dependencies"
  LINT_CMD="./android/gradlew lint"
  TYPECHECK_CMD=":"
  TEST_CMD="./android/gradlew test"
fi

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
