# Usage

See prerequisites and setup instructions in the [README](README.md) before following the steps below.

The following CLI commands assume an initialized database and an active virtual environment.
The database tables `bin_activity`, `nfc_tag_mapping`, `tour`, `bin_visit` and `vehicle_emptying` should be empty before running the commands below.

## Configuration
All pipelines can be configured via the `.yaml` files in the `config` directory. 
- The base configuration is provided in `config/base.yaml`. 
- Service schedule parameters can be configured in `config/schedule.yaml`.
- Parameters concerning the fill level simulation can be configured in `config/latent_filllevel.yaml`.


## bin activity pipeline:
Run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-bin-activity --config config/base.yaml
   ```

- The command should output `Loaded bins` and `Generated bin_activity rows`.
- The generate data is stored in the `bin_activity` table.

---

## NFC tag mapping pipeline:
Run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-nfc-tag-mapping --config config/base.yaml
   ```

- The command should output `Loaded Bins` and `Generated nfc_tag_mapping rows`.
- The generate data is stored in the `nfc_tag_mapping` table.

---

## tour pipeline:
Run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-tours --config config/base.yaml
   ```

- The command should output `Generated tour rows`, and `Generation days`.
- The generate data is stored in the `tour` table.
---

## tour item pipeline:
First prepare the data as follows:

1. Build a bin to neighbourhood mapping CSV for generator preprocessing:
   ```bash
   python scripts/assign_bins_to_neighbourhoods.py
   ```
   - Reads polygons from `/data/neighbourhoods.geojson`
   - Writes output to `data/static/bin_neighbourhood_mapping.csv`.

- The command outputs a short summary of the number of bins assigned to each neighbourhood.
- Under `/data/static/bin_neighbourhood_mapping.csv`, each row corresponds to a bin-to-neighbourhood assignment

2. Download and prepare historical weather data for Neuchatel:
   ```bash
   python scripts/prepare_historical_weather_neuchatel.py --config config/base.yaml
   ```
   - Downloads data from:
     - `https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/neu/ogd-smn_neu_d_historical.csv` (up to 2025)
     - `https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/neu/ogd-smn_neu_d_recent.csv` (2026 until yesterday)
   - Removes rows before `config.simulation.start_date`
   - Writes `data/static/historical_weater_neuchatle_DD-MM-YYYY.csv`

- The command outputs a summary of the number of rows downloaded and written to the output file.
- Under `data/static/historical_weater_neuchatle_DD-MM-YYYY.csv`, each row corresponds to a day and contains the considered weather parameters for that day.

Then run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-tour-items --config config/base.yaml
   ```
 
- The command should output `Generated bin_visit rows`, and `Generated vehicle_emptying rows`.
- The generated data is stored in the `bin_visit` and `vehicle_emptying` tables, respectively.