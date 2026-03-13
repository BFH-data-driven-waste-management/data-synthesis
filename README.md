# Thesis - Data Synthetization

- Dockerized PostgreSQL database with sql-scheme of `Project 2`.
- Simulation-based data generation for Thesis data foundation.

## Usage
1. Provide environment variables in `.env` file for the database container.
2. Start the container:
   ```bash
   docker compose up -d
   ```
3. Connect to DB:
   ```bash
   psql postgresql://postgres:postgres@localhost:5432/postgres
   ```


## Python setup (pipeline)
1. Create and activate a virtual environment:
   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies centrally from `requirements.txt`:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Configure database DSN via env var (or `database.dsn` in YAML):
   ```bash
   export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
   ```
4. Run the bin activity pipeline:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-bin-activity --config config/base.yaml
   ```

## Notes
- Scripts in `/docker-entrypoint-initdb.d` run only on first initialization of the data volume.
- To re-run schema initialization, remove the `postgres-data` volume first:
  ```bash
  docker compose down -v
  docker compose up -d
  ```
