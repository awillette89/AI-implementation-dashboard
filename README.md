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
- `sql/` contains the five study metrics and the algorithm turnaround report.
- `tests/` is reserved for checks as the project grows.

## First step

Install the project's third-party dependencies from the project folder
(Python 3.10 or newer is required):

```powershell
python -m pip install -r requirements.txt
```

Pandas supports the data scripts, and Streamlit displays the dashboard.
SQLite is included with Python and does not need a separate installation.

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

## Fourth SQL metric: turnaround time

Run the turnaround-time report from the project folder against the SQLite database:

```powershell
python src/run_sql_file.py sql/04_turnaround_time.sql
```

Turnaround time is the elapsed time from `study_start_time` to
`study_complete_time`, measured in minutes. The report shows four result sets:
the overall average, averages by site, averages by modality, and a comparison
of AI-processed studies with studies not processed by AI. Each average is
rounded to one decimal place. Missing or unrecognized timestamps are excluded
from the averages.

The comparison includes all studies, so the group not processed by AI also
includes studies that were not eligible for AI. This mock dataset cannot
establish that AI caused any turnaround-time difference. Differences may
reflect the mix of sites, modalities, or other study characteristics.

## Fifth SQL metric: AI adoption

Run the adoption report from the project folder:

```powershell
python src/run_sql_file.py sql/05_ai_adoption.sql
```

Adoption asks whether radiologists used the AI results available to them.
The adoption rate is the number of studies where the radiologist used AI,
among studies with an AI result available, divided by the number of studies
with an AI result available, multiplied by 100.

The report filters to `ai_result_available = 1` and uses
`radiologist_used_ai = 1` to count adoption. It prints counts and percentages
overall, by site, and by modality, rounded to one decimal place.
Utilization measures whether eligible studies entered AI processing, while
adoption measures whether available results were actually used.

If no AI results are available, the overall counts are zero and the rate is
NULL (undefined), rather than zero percent. Sites and modalities with no
available AI results do not appear in the grouped results.

## Python summary: all five overall metrics

From the project folder, run:

```powershell
python src/summarize_metrics.py
```

This prints total studies, AI utilization, AI error rate, average turnaround
time, and AI adoption, including the counts behind each percentage. It reuses
the first query from each SQL report through `read_select_statements`, keeping
the metric definitions in the SQL files. Undefined rates or averages appear
as `N/A`, and counts with no matching studies appear as zero.

The script opens the database in read-only mode and does not modify it.
Database and SQL paths are based on the script's location. To run it from
another folder, pass the full path to `summarize_metrics.py` to Python.

## Local Streamlit dashboard

The dashboard is organized into three tabs:

- **Overview:** five metric cards and study count by modality.
- **AI usage & reliability:** the current utilization chart and supporting counts.
- **Algorithm turnaround:** algorithm selection and the two TAT averages with sample counts.

The Site dropdown sits above the tabs and applies to all three. **Showing:**
identifies the current site. Shorter metric labels have help tooltips with
their definitions, and **How these metrics work** expands the detailed
explanations. The simulated-data notice stays visible above the tabs.

From the project folder, launch the dashboard:

```powershell
python -m streamlit run src/app.py
```

Open the local URL printed in the terminal if the browser does not open
automatically. Keep the terminal running while using the dashboard, and press
Ctrl+C in that terminal to stop it.

The page displays five overall metric cards with short explanations and a
simulated-data notice. It shares `load_overall_metrics()` in
`src/summarize_metrics.py` with the terminal summary, so both read the first
query from each existing SQL report and use the same calculations. The database
is opened read-only, and undefined metrics display as `N/A`.

Use the **Site** dropdown to view all studies or one site's studies. It defaults
to **All sites** and reads the site names from SQLite. Changing the selection
reruns the page and updates all five cards. Each metric keeps its original
denominator within the selected site (eligible studies for utilization,
AI-processed studies for error rate, and available results for adoption).
Switching back to **All sites** restores the overall values.

The shared loader accepts an optional site and supplies filtered study rows to
the existing SQL formulas. It passes the site as a SQL parameter, keeping site
names separate from SQL code. The terminal summary continues to show all sites,
and the standalone SQL reports continue to work unchanged.

Below the cards, **Study volume by modality** shows a bar for each modality
present in the selected scope. The horizontal axis is **Modality**, and the
vertical axis is **Number of studies**. This chart includes all studies,
regardless of AI eligibility or processing, and follows the same Site dropdown.
The modality counts add up to the total-studies card.

The shared `load_modality_volumes()` function uses SQL `GROUP BY` to count
studies for each modality, with a parameter for the optional site filter and
a read-only database connection. If no studies match, the page shows a helpful
message instead of an empty chart. After adding new shared functions, restart
Streamlit with Ctrl+C followed by the launch command if a browser refresh
does not pick up the changes.

Database and SQL paths are relative to the scripts, not the terminal folder.
To launch from elsewhere, pass the full path to `src/app.py` in the command.
If the database is missing, run the data-generation and loading steps above.

Below the volume chart, **AI utilization by modality** shows the percentage
of eligible studies processed by AI, using the same Site selection. Its axes
are **Modality** and **AI utilization (%)**. A supporting table shows the
eligible-study count, the eligible studies processed by AI, and the percentage.
Modalities with no eligible studies are excluded. If none qualify, a helpful
message appears instead of the chart and table.

`load_modality_utilization()` reuses the third query in
`sql/02_ai_utilization.sql`, preserving its formula and eligibility denominator.
The shared site-filter helper passes site names as SQL parameters and the
loader opens SQLite read-only. Counts from this table sum to the eligible and
processed counts for the selected site's utilization metric. The overall
percentage is based on these counts, not a simple average of modality rates.

## Algorithm examples and turnaround time

The same 500-row study table now includes `algorithm_name`, `algorithm_vendor`,
and a mock `protocol`. Each eligible study has one assigned algorithm.
The source catalog is `data/ai_algorithms.csv`, with product links and the date
checked. These are representative examples, not a ranking of the best products:

- [Aidoc ICH](https://www.aidoc.com/solutions/neuro/) and
  [Aidoc PE](https://www.aidoc.com/solutions/vte-solutions/).
- [Viz ICH](https://www.viz.ai/indications-for-use) and
  [Viz PE](https://www.viz.ai/news/new-clinical-data-supports-viz-ai-solution-for-improved-pulmonary-embolism-detection-and-care-coordination).
- [Rapid ICH](https://www.rapidai.com/press-release/rapid-platform-expands-to-address-hemorrhagic-stroke)
  and [Rapid ASPECTS](https://www.rapidai.com/press-release/rapid-aspects-first-neuroimaging-solution-with-cadx-fda-clearance).
- [icobrain ms](https://www.icometrix.com/multiple-sclerosis) from icometrix.

Product names and broad tasks are real. All assignments, protocols, times,
errors, and usage statistics are simulated. Protocol matching is simplified,
not a full implementation of product labeling or clinical eligibility.
All products use the same invented timing/probability distributions, so this
data cannot rank vendors or establish that AI caused a study-TAT difference.

To add algorithm assignments to an existing dataset and load them:

```powershell
python src/add_algorithm_data.py
python src/load_to_sqlite.py
```

This preserves study IDs, sites, modalities, and study start/completion times.
It saves the prior CSV and database under `data/backups/` before replacing AI
assignments and timestamps. The regular mock-data generator also includes the
new algorithm assignments. AI utilization, errors, and adoption change because
the old generic eligibility rule is replaced by the mock algorithm matches.
The total study count and overall study TAT remain unchanged.

Run the new report:

```powershell
python src/run_sql_file.py sql/06_algorithm_turnaround.sql
```

It shows processed counts, successful results, errors, and two averages:

- **AI processing TAT:** AI start to result available, for successful results.
- **Study TAT:** study start to completion, for studies processed by that
  algorithm, including errors. This is not order-to-read time.

Algorithms with no processed studies do not appear. A missing average means
no qualifying results, not zero minutes. Different tasks and small samples
make these descriptive mock statistics, not vendor performance comparisons.
The dashboard also has a **Turnaround time by algorithm** section. Its table
shows both TAT averages with processed counts, successful results, and errors.
Use the Algorithm dropdown to look up a product, or select All algorithms to
see the table together. This dropdown affects only the algorithm table. The
existing Site dropdown filters the entire page, including algorithm timings.
Only algorithms with processed studies at the selected site appear. Missing
timings display as N/A. Restart Streamlit after this update to load the new
shared function.
