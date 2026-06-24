# On Windows, use 'py -m pip' and 'py -m pytest' if bare commands fail.

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

demo:
	python demo/generate_dataset.py
	@echo "Dataset written to demo/incidents.csv"

test:
	pytest tests/ -v
