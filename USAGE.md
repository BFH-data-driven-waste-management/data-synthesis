# Usage

1. Provide environment variables in `.env` file for the database container.
2. Start the container:
   ```bash
   docker compose up -d
   ```
3. Connect to DB:
   ```bash
   psql postgresql://postgres:postgres@localhost:5432/postgres
   ```

## Python setup
1. Create and activate a virtual environment:
   ```bash
   apt install python3.11-venv
   python3.11 -m venv .venv
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
   
## Data generation
1. Run the bin activity pipeline:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-bin-activity --config config/base.yaml
   ```
2. Run the NFC tag mapping pipeline:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-nfc-tag-mapping --config config/base.yaml
   ```
3. Run the tour pipeline:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-tours --config config/base.yaml
   ```
4. Build a bin to neighbourhood mapping CSV for generator preprocessing:
   ```bash
   python scripts/assign_bins_to_neighbourhoods.py
   ```
   - Reads polygons from `/data/neighbourhoods.geojson`
   - Writes output to `data/static/bin_neighbourhood_mapping.csv`.

5. Download and prepare historical weather data for Neuchatel:
   ```bash
   python scripts/prepare_historical_weather_neuchatel.py --config config/base.yaml
   ```
   - Downloads data from:
     - `https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/neu/ogd-smn_neu_d_historical.csv` (up to 2025)
     - `https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/neu/ogd-smn_neu_d_recent.csv` (2026 until yesterday)
   - Removes rows before `simulation.start_date`
   - Writes `data/static/historical_weater_neuchatle_DD-MM-YYYY.csv`

6. Run the tour item pipeline:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-tour-items --config config/base.yaml
   ```

## Notes
- Scripts in `/docker-entrypoint-initdb.d` run only on first initialization of the data volume.
- To re-run schema initialization, remove the `postgres-data` volume first:
  ```bash
  docker compose down -v
  docker compose up -d
  ```
