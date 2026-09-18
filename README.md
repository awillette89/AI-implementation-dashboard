# AI Implementation Dashboard

This learning project simulates the rollout of an artificial-intelligence (AI)
tool in an imaging workflow. It will use mock imaging-study data to explore the
questions an implementation team would ask:

- How many studies are processed?
- How often do eligible studies use AI?
- What is the turnaround time from study start to completion?
- How often does the AI workflow produce an error?
- Are radiologists adopting the AI result in their workflow?

## Project layout

- `data/` stores the generated mock dataset.
- `src/` contains Python scripts.
- `sql/` will later contain SQL metric queries.
- `tests/` is reserved for checks as the project grows.

## First step

Run the mock-data generator from the project folder:

```powershell
python src/generate_mock_data.py
```

It creates `data/imaging_studies.csv` with 500 simulated studies.

## Second step

Load the CSV into a local SQLite database:

```powershell
python src/load_to_sqlite.py
```

This creates `data/ai_implementation.db` and replaces its
`imaging_studies` table with the CSV's current contents. The script also runs a
simple row-count query to confirm that the import worked.

## First SQL metric: studies processed

Run the first SQL report against the SQLite database:

```powershell
python src/run_sql_file.py sql/01_studies_processed.sql
```

It prints three result sets: the total study count, daily study volume, and a
site-and-modality volume breakdown.

## Second SQL metric: AI utilization

Run the AI-utilization report against the SQLite database:

```powershell
python src/run_sql_file.py sql/02_ai_utilization.sql
```

It shows the number of eligible studies, the number processed by AI, and the
resulting utilization percentage overall, by site, and by modality.

## Third SQL metric: AI error rate

Run the AI error-rate report against the SQLite database:

```powershell
python src/run_sql_file.py sql/03_ai_error_rate.sql
```

It shows the number of AI-processed studies, the number that had an error, and
the resulting error rate overall, by site, and by modality.
