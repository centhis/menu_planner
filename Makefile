.PHONY: help setup up down test lint typecheck format format-check migrate migration-status smoke m8-fake-integration check clean clean-runtime

help setup up down test lint typecheck format format-check migrate migration-status smoke m8-fake-integration check clean clean-runtime:
	@scripts/dev.sh $@
