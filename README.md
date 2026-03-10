# Thesis - Data Synthetization

- Dockerized PostgreSQL database with sql-scheme of `Project 2`.
- Simulation-based data generation for `Thesis` data foundation.

## Usage
1. Provide environment variables in `.env` file.
2. Start the container:
   ```bash
   docker compose up -d
   ```
3. Connect to DB:
   ```bash
   psql postgresql://postgres:postgres@localhost:5432/postgres
   ```

## Notes
- Scripts in `/docker-entrypoint-initdb.d` run only on first initialization of the data volume.
- To re-run schema initialization, remove the `postgres-data` volume first:
  ```bash
  docker compose down -v
  docker compose up -d
  ```
