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

gif:
	@echo "To record a terminal demo:"
	@echo "  1. make run          # start the server (keep this terminal open)"
	@echo "  2. asciinema rec demo/demo.cast --command 'bash demo/run_demo.sh'"
	@echo "  3. agg demo/demo.cast demo/demo.gif   # convert to GIF (npm i -g agg)"
	@echo ""
	@echo "Or just run: bash demo/run_demo.sh  (server must be running)"
