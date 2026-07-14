ruff = uv tool run ruff@latest

all: format run

check:
	${ruff} check
	${ruff} format --check
format:
	${ruff} check --fix
	${ruff} format

run:
	uv run main.py out/
