.PHONY: claude-init
claude-init:
	@if [ ! -f .claude/settings.json ]; then \
		cp .claude/settings.example.json .claude/settings.json; \
		echo "Created .claude/settings.json from .claude/settings.example.json"; \
	else \
		echo ".claude/settings.json already exists; leaving it unchanged"; \
	fi

.PHONY: claude-check
claude-check:
	@test -f CLAUDE.md || (echo "Missing CLAUDE.md" && exit 1)
	@test -d .claude || (echo "Missing .claude directory" && exit 1)
	@test -f .claude/settings.example.json || (echo "Missing .claude/settings.example.json" && exit 1)
	@echo "Claude Code files are present"
