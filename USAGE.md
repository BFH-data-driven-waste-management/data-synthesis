# Usage

See prerequisites and setup instructions in the [README](README.md) before following the steps below.

The following CLI commands assume an initialized database and an active virtual environment.
The database tables `bin_activity`, `nfc_tag_mapping`, `tour`, `bin_visit` and `vehicle_emptying` should be empty before running the commands below.

## Configuration
All pipelines can be configured via the `.yaml` files in the `config` directory. 
- The base configuration is provided in `config/base.yaml`. 
- Service schedule parameters can be configured in `config/schedule.yaml`.
- Parameters concerning the fill level simulation can be configured in `config/latent_filllevel.yaml`.


## Bin Activity pipeline:
Run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-bin-activity --config config/base.yaml
   ```
Output:
- The command should output `Loaded bins` and `Generated bin_activity rows`.
- The generate data is stored in the `bin_activity` table.

---

## NFC Tag Mapping pipeline:
Run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-nfc-tag-mapping --config config/base.yaml
   ```
Output:
- The command should output `Loaded Bins` and `Generated nfc_tag_mapping rows`.
- The generate data is stored in the `nfc_tag_mapping` table.

---

## Tour pipeline:
Run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-tours --config config/base.yaml
   ```
Output:
- The command should output `Generated tour rows`, and `Generation days`.
- The generate data is stored in the `tour` table.
---

## Prepare neighborhood data
Build a bin to neighbourhood mapping CSV for generator preprocessing:
   ```bash
   python scripts/assign_bins_to_neighbourhoods.py
   ```
Output:
- The command outputs a short summary of the number of bins assigned to each neighbourhood.
- Under `/data/static/bin_neighbourhood_mapping.csv`, each row corresponds to a bin-to-neighbourhood assignment

---

## Prepare historical weather data

Download and prepare historical weather data for Neuchatel:
   ```bash
   python scripts/prepare_historical_weather_neuchatel.py --config config/base.yaml
   ```

Hint:
- on macOS, you may need to run pythons certificate installer first to avoid SSL errors when downloading the data:
   ```bash
   /Applications/Python\ 3.11/Install\ Certificates.command
   ```

Output:
- The command outputs a summary of the number of rows downloaded and written to the output file.
- Under `data/static/historical_weater_neuchatle_DD-MM-YYYY.csv`, each row corresponds to a day and contains the considered weather parameters for that day.


---
## Tour items pipeline:
Run with:
   ```bash
   PYTHONPATH=src python -m data_synthesization.main generate-tour-items --config config/base.yaml
   ```
Output:
- The command should output `Generated bin_visit rows`, and `Generated vehicle_emptying rows`.
- The generated data is stored in the `bin_visit` and `vehicle_emptying` tables, respectively.