.PHONY: test build clean dev

test:
	uv run pytest -v

dev:
	uv run python bin/dev.py

build:
	@bash bin/build.sh

clean:
	rm -rf build/
