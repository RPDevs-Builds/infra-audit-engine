# Makefile for LLM-UserProfile Infrastructure Audit
# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/Makefile

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
DIST = dist/orchestrator

.PHONY: help init build run clean distclean enroll

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

init: ## Initialize virtual environment and install requirements
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

build: init ## Compile the project into a standalone executable using PyInstaller
	$(VENV)/bin/pyinstaller --onefile \
		--name orchestrator \
		--add-data "docs:docs" \
		--add-data ".env:." \
		src/orchestrator.py

run: ## Execute the compiled binary
	@if [ -f $(DIST) ]; then ./$(DIST); else echo "Binary not found. Run 'make build' first."; fi

enroll: init ## Interactive helper to enroll a new audit target into .env
	$(PYTHON) src/enroll.py

clean: ## Remove build and distribution artifacts
	rm -rf dist build *.spec

distclean: clean ## Remove build artifacts and the virtual environment
	rm -rf $(VENV)
