
  ## Running the code

  Run `pip install -r requirements.txt` to install the dependencies.

  Run `cqlsh -f init_schema.cql` to install migrations

  Run `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` to start fast api service.

  Run `docker compose up -d` to start db.
  