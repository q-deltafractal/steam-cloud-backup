ruff = uv run --dev -m ruff

all: format run

init:
	git config core.hooksPath .githooks

check:
	${ruff} check
	${ruff} format --check
format:
	${ruff} format
	${ruff} check --fix

run:
	uv run steamcb/cli.py out/

pre_commit:
	.githooks/pre-commit
