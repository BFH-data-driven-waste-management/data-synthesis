# Synthetic Data

This repository contains code and data for the synthetic data generation component used in the thesis under consideration of `Project 2`'s data model.

The data is generated based on real-world inputs such as bin locations, weather data, and events.
Realistic assumptions are made about the data because no sufficient empirical data is available.
All generation assumptions, implementation details, and results are described in the thesis report.

The repository includes four data generation pipelines.
More implementation details are described in the thesis report.

---
## Repository Structure

- `/config` - configuration files for the pipelines.
- `/data` - raw and preprocessed data.
- `/scripts` - utility scripts for data preparation and processing.
- `/sql` - sql seeding of schema and master data.
- `/src` 
  - `/pipelines` - central entrypoint for each generation pipeline.
  - `/feature` - generation features logic, per pipeline.
  - `/shared` - shared logic such as database access, configuration, datastructures, and utils.
  - `/validation` - validation modules, per pipeline.
  - `/main.py` - entrypoint for the pipelines.


---
## Execution model

Local execution is based on a Docker Compose service that initializes and starts a PostgreSQL database.
Further development execution is based on locally installed software.
Only the database is containerized.


---
## Prerequisites

### Operating System
The implementation runs on Ubuntu and macOS.
The following versions are tested:
- Ubuntu 22.04.3 LTS (WSL2)
- macOS 26.4.1

### Software
- Docker (engine version >=20)
- Docker Compose (version >=2)
- Python (tested on 3.11)

### Data
All required data is provided in `/data` and `/sql`.


---
## Environment setup

### Initial 

1. Install python3.11 and python3-venv. (Ubuntu and macOS variants below)
```bash
apt install python3.11-venv
```
```bash
brew install python3.11-venv
```
2. Create a virtual environment and activate it. 
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```
3. Install dependencies centrally from `requirements.txt`:
```bash
python -m pip install -r requirements.txt
```

### Before each use
1. Start the database container (see .env.default for config options):
```bash
docker compose up -d
```
2. Activate the virtual environment:
```bash
source .venv/bin/activate
```
3. Provide the database url environment variable:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
```

### Check
You should now have a running installation of python3.11 and an active virtual environment.
```bash
echo $VIRTUAL_ENV
```
Should return the path to the virtual environment.
```bash
python --version
```
Should return `Python 3.11.x`.

---
## Usage
Consult [USAGE.md](USAGE.md) for detailed usage instructions.


---
## Additional information

- Scripts in `/sql` run only on first initialization of the data volume.
- To re-run schema initialization, remove the `postgres-data` volume first:
  ```bash
  docker compose down -v
  docker compose up -d
  ```

---
## Authors

- Affolter Marco, [marco.affolter2@students.bfh.ch](mailto:marco.affolter.2@students.bfh.ch)
- Scherer Janic, [janic.scherer@students.bfh.ch](mailto:janic.scherer@students.bfh.ch)
- Scherer Luca, [luca.scherer@students.bfh.ch](mailto:luca.scherer@students.bfh.ch)

---
## License

Copyright (c) 2026 Affolter Marco, Scherer Janic, Scherer Luca. All rights reserved.

This repository is made available for academic, educational, and research purposes only. Commercial use, redistribution, sublicensing, hosted use, or use in production systems requires prior written permission from the copyright holders. See the [LICENSE](./LICENSE) file for details.