NAME = a_maze_ing.py
PYTHON = python3
POETRY = $(HOME)/.local/bin/poetry

all: install lint run

install:
	@echo "Checking if Poetry is installed..."
	@if ! [ -f $(POETRY) ]; then \
		echo "Poetry not found. Installing Poetry..."; \
		curl -sSL https://install.python-poetry.org | $(PYTHON) -; \
	fi
	@echo "Installing project dependencies..."
	@$(POETRY) install
	@echo "Updating pip and installing pygame..."
	@$(POETRY) run $(PYTHON) -m pip install --upgrade pip
	@$(POETRY) run pip install pygame

run:
	@PYGAME_HIDE_SUPPORT_PROMPT=1 $(POETRY) run $(PYTHON) $(NAME) config.txt

debug:
	@PYGAME_HIDE_SUPPORT_PROMPT=1 $(POETRY) run $(PYTHON) -m pdb $(NAME) config.txt

clean:
	@echo "Cleaning cache and build files..."
	@rm -rf .mypy_cache dist build *.lock
	@find . -type d -name "__pycache__" | xargs rm -rf

lint:
	@echo "Running mandatory lint..."
	@$(POETRY) run flake8 .
	@$(POETRY) run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	@echo "Running strict lint..."
	@$(POETRY) run flake8 .
	@$(POETRY) run mypy . --strict

package:
	@echo "Building reusable package mazegen..."
	@$(POETRY) build

.PHONY: install run debug clean lint lint-strict package
