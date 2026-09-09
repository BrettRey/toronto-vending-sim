PY ?= python3

.PHONY: test demo play catalogue locations clean

test:
	$(PY) -m unittest discover -s tests -v

demo:
	$(PY) -m vendsim run --plan plans/example-plan.json --out runs/demo

play:
	$(PY) -m vendsim play

catalogue:
	$(PY) -m vendsim catalogue

locations:
	$(PY) -m vendsim locations

clean:
	rm -rf runs/demo vendsim/__pycache__ tests/__pycache__
