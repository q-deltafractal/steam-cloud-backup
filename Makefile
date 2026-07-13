ruff = uvx ruff

all: format run

check:
	${ruff} check
	${ruff} format --check
format:
	${ruff} check --fix
	${ruff} format

run:
	uv run main.py

