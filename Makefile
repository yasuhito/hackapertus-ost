IMAGE ?= hackapertus-ost:local
INPUT_DIR ?= $(CURDIR)/track_2a/data
OUTPUT_DIR ?= $(CURDIR)/output
BOOKLET_DIR ?= $(CURDIR)/booklets
INPUT ?= /data/cases.jsonl
OUTPUT ?= /output/predictions.jsonl
LLM_BACKEND ?= openai
PYTHON ?= python3
PIPELINE ?= C
TOOL_STEP ?= baseline
DOCKERFILE = $(if $(filter A B C,$(PIPELINE)),Dockerfile.agent,Dockerfile)
RUNTIME_FLAGS = $(if $(filter A B C,$(PIPELINE)),--read-only --tmpfs /tmp)

.PHONY: run build run-local test dev-eval download prepare
build:
	docker build --platform linux/amd64 -f $(DOCKERFILE) -t $(IMAGE) .
run: build
	mkdir -p "$(OUTPUT_DIR)" "$(BOOKLET_DIR)"
	docker run --rm $(RUNTIME_FLAGS) --user "$$(id -u):$$(id -g)" \
	  -e BASE_URL -e API_KEY -e LLM_BASE_URL -e LLM_API_KEY -e PUBLICAI_API_KEY -e LLM_MODEL -e LLM_NAME \
	  -e LLM_USER_AGENT -e LLM_TIMEOUT -e LLM_MAX_OUTPUT_TOKENS -e LLM_BACKEND=$(LLM_BACKEND) -e PIPELINE=$(PIPELINE) -e TOOL_STEP=$(TOOL_STEP) \
	  -v "$(INPUT_DIR):/data:ro" -v "$(OUTPUT_DIR):/output" \
	  -v "$(BOOKLET_DIR):/booklets:ro" \
	  $(IMAGE) --input "$(INPUT)" --output "$(OUTPUT)"
run-local:
	$(PYTHON) track_2a/src/predict.py --backend $(LLM_BACKEND) --input "$(INPUT_DIR)/cases.jsonl" --output "$(OUTPUT_DIR)/predictions.jsonl"
test:
	$(PYTHON) -m pytest -q track_2a/tests
download:
	$(PYTHON) track_2a/scripts/download_dataset.py
	$(PYTHON) track_2a/scripts/download_booklets.py --output-dir "$(BOOKLET_DIR)"
prepare:
	$(PYTHON) track_2a/scripts/prepare_data.py --pdf-dir "$(BOOKLET_DIR)"
dev-eval:
	mkdir -p output
	$(PYTHON) track_2a/src/predict.py --backend mock --input track_2a/data/dev_cases.jsonl --output output/dev_predictions.jsonl
	$(PYTHON) track_2a/src/score.py --gold track_2a/data/dev_gold.jsonl --predictions output/dev_predictions.jsonl --output output/dev_score.json
	$(PYTHON) track_2a/src/predict.py --backend mock --input track_2a/data/dev_advanced_cases.jsonl --output output/dev_advanced_predictions.jsonl
	$(PYTHON) track_2a/src/score.py --gold track_2a/data/dev_advanced_gold.jsonl --predictions output/dev_advanced_predictions.jsonl --output output/dev_advanced_score.json

.PHONY: roast-version roast-test roast-smoke
roast-version:
	track_2a/dev/roast/bundle.sh exec roast version
roast-test:
	TEST_PYTHON="$(PYTHON)" ROAST_PYTHON="$(PYTHON)" track_2a/dev/roast/bundle.sh exec ruby track_2a/dev/roast/test_measurement.rb
roast-smoke:
	ROAST_PYTHON="$(PYTHON)" track_2a/dev/roast/bundle.sh exec roast execute track_2a/dev/roast/workflow.rb
