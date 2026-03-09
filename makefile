.PHONY: embed_feature_docs run_evaluation test

embed_feature_docs:
	uv run python -m app.utils.index_metadata

run_evaluation:
	uv run python -m app.utils.run_validation --username chc --password chc419

test:
	@echo "yes"