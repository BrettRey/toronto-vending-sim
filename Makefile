PY ?= python3

.PHONY: test demo play web catalogue locations clean

test:
	$(PY) -m unittest discover -s tests -v
	@command -v node >/dev/null && node tests/test_engine.mjs || echo "node not found; JavaScript engine tests skipped"

web:
	$(PY) scripts/build_web.py

demo:
	$(PY) -m vendsim run --plan plans/example-plan.json --out runs/demo

play:
	$(PY) -m vendsim play

catalogue:
	$(PY) -m vendsim catalogue

locations:
	$(PY) -m vendsim locations

clean:
	rm -rf runs/demo vendsim/__pycache__ tests/__pycache__ scripts/__pycache__
