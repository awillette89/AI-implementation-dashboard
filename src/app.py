"""A first Streamlit dashboard using the project's existing SQL metrics."""

import sqlite3

import pandas as pd
import streamlit as st

from summarize_metrics import (
    format_value, load_algorithm_turnaround, load_modality_utilization, load_modality_volumes,
    load_overall_metrics, load_sites,
)


def main() -> None:
    # Streamlit builds the page in the same order as these Python statements.
    st.set_page_config(page_title="AI Implementation Dashboard", layout="wide")
    st.title("AI Implementation Dashboard")
    st.caption("An overview of the mock imaging-AI workflow")
    st.info(
        "This data is simulated for learning. Real algorithm names do not imply "
        "measured vendor performance. It cannot establish that AI caused "
        "any turnaround-time difference."
    )

    # Both this page and the terminal summary use the same read-only loader.
    # SQL still performs all calculations. Python chooses how to display them.
    try:
        # None means no site filter. The first option is selected by default.
        # Actual site names come from SQLite instead of a hard-coded list.
        selected_site = st.selectbox(
            "Site",
            options=[None, *load_sites()],
            format_func=lambda site: "All sites" if site is None else site,
        )
        # Changing the dropdown reruns this script from top to bottom.
        # The new selection is passed to the loader before cards are drawn.
        metrics = load_overall_metrics(site=selected_site)
    except (OSError, sqlite3.Error, ValueError) as error:
        st.error(f"Could not load the metrics: {error}")
        st.stop()

    st.markdown(f"**Showing: {'All sites' if selected_site is None else selected_site}**")

    # Tabs organize existing displays. The Site selection above is shared by
    # all three helpers, so changing it updates every tab consistently.
    overview_tab, usage_tab, algorithm_tab = st.tabs(
        ["Overview", "AI usage & reliability", "Algorithm turnaround"]
    )
    with overview_tab:
        render_overview(metrics, selected_site)
    with usage_tab:
        render_usage(selected_site)
    with algorithm_tab:
        render_algorithms(selected_site)

    # Keep longer explanations available without filling the main view.
    with st.expander("How these metrics work"):
        st.markdown(
            "- **Studies:** all studies in the selected site scope.\n"
            "- **AI utilization:** eligible studies processed by AI / eligible studies.\n"
            "- **AI errors:** processed studies with an error / processed studies.\n"
            "- **AI adoption:** results used / studies with an available result.\n"
            "- **Study TAT:** average study start to completion, in minutes.\n"
            "- **AI processing TAT:** average AI start to successful result, in minutes.\n\n"
            "Percentages multiply these fractions by 100. N/A means there are no "
            "qualifying values. Algorithm TAT uses only that algorithm's processed "
            "studies; successful results supply its AI processing average. "
            "Small samples and different clinical tasks do not support vendor rankings."
        )


def render_overview(metrics: dict, selected_site: str | None) -> None:
    """Show the overall cards and study-volume chart."""
    # Each card identifies a result column and adds a plain-English definition.
    cards = [
        ("Studies", "Studies processed", "total_studies_processed", "count",
         "All imaging studies in the selected scope, whether or not AI processed them."),
        ("AI utilization", "AI utilization", "ai_utilization_percent", "percent",
         "The percentage of AI-eligible studies that were processed by AI."),
        ("AI errors", "AI error rate", "ai_error_rate_percent", "percent",
         "The percentage of AI-processed studies that had an AI error."),
        ("Study TAT", "Turnaround time", "avg_turnaround_minutes", "minutes",
         "Average minutes from study start to study completion."),
        ("AI adoption", "AI adoption", "ai_adoption_rate_percent", "percent",
         "Among studies with an AI result available, the percentage where the radiologist used it."),
    ]

    # Two rows keep the five cards readable. Columns place cards side by side.
    for row_cards in (cards[:3], cards[3:]):
        for column, (label, report, field, kind, explanation) in zip(
            st.columns(len(row_cards)), row_cards
        ):
            with column:
                with st.container(border=True):
                    # st.metric displays one labeled number. Shared formatting
                    # shows undefined values as N/A instead of implying zero.
                    st.metric(label, format_value(metrics[report][field], kind), help=explanation)

    st.caption("N/A means there is not enough applicable data to calculate the metric.")

    st.subheader("Study count by modality")
    st.caption("All studies in the selected scope, regardless of AI eligibility or processing.")
    try:
        modality_volumes = load_modality_volumes(site=selected_site)
    except (OSError, sqlite3.Error) as error:
        st.error(f"Could not load study volume: {error}")
        return

    if not modality_volumes:
        st.info("No studies match the selected site. Choose another site or All sites.")
    else:
        # The query returns one row per modality. A DataFrame gives those rows
        # named columns that Streamlit can use for the chart's two axes.
        chart_data = pd.DataFrame(modality_volumes).rename(
            columns={"modality": "Modality", "study_count": "Number of studies"}
        )
        chart_data["Modality"] = chart_data["Modality"].fillna("Unknown")
        # Each bar's height is the count from SQL, not an AI-only count.
        # The column names also provide readable axis labels.
        st.bar_chart(chart_data, x="Modality", y="Number of studies")



def render_usage(selected_site: str | None) -> None:
    """Show the existing utilization chart and supporting counts."""
    st.subheader("AI utilization by modality (%)")
    st.caption(
        "Percentage of eligible studies processed by AI in the selected scope. "
        "Modalities with no eligible studies are excluded."
    )
    try:
        modality_utilization = load_modality_utilization(site=selected_site)
    except (OSError, sqlite3.Error, ValueError) as error:
        st.error(f"Could not load AI utilization: {error}")
        return

    if not modality_utilization:
        st.info("No AI-eligible studies match this selection. Choose another site or All sites.")
    else:
        # Both displays use the same SQL result. Python only renames columns
        # for readability, so the utilization formula stays in the SQL report.
        utilization_data = pd.DataFrame(modality_utilization).rename(columns={
            "modality": "Modality",
            "ai_eligible_studies": "Eligible studies",
            "eligible_studies_ai_processed": "Eligible studies processed by AI",
            "ai_utilization_percent": "AI utilization (%)",
        })
        utilization_data["Modality"] = utilization_data["Modality"].fillna("Unknown")
        # Selecting x and y plots percentages rather than the supporting counts.
        # These column names also label the horizontal and vertical axes.
        st.bar_chart(utilization_data, x="Modality", y="AI utilization (%)")
        st.caption("Counts behind the percentages")
        # Format percentages only in the table, keeping chart values numeric.
        table_data = utilization_data.copy()
        table_data["AI utilization (%)"] = table_data["AI utilization (%)"].map(
            lambda value: format_value(value, "percent")
        )
        st.dataframe(table_data, hide_index=True)



def render_algorithms(selected_site: str | None) -> None:
    """Keep algorithm lookup in its own tab."""
    st.subheader("Turnaround time by algorithm")
    st.caption(
        "Simulated timings, not vendor benchmarks. AI processing time measures AI "
        "start to successful result. Study turnaround measures study start to "
        "completion among AI-processed studies, including errors."
    )
    try:
        algorithm_rows = load_algorithm_turnaround(site=selected_site)
    except (OSError, sqlite3.Error, ValueError) as error:
        st.error(f"Could not load algorithm timings: {error}")
        st.caption("Run add_algorithm_data.py and load_to_sqlite.py if your database needs updating.")
        return

    if not algorithm_rows:
        st.info("No algorithm-processed studies match this site. Try All sites.")
    else:
        # This dropdown affects only the algorithm table. The Site dropdown
        # above still limits the data for the entire page.
        selected_algorithm = st.selectbox(
            "Algorithm (turnaround table only)",
            options=[None, *sorted(row["algorithm_name"] for row in algorithm_rows)],
            format_func=lambda value: "All algorithms" if value is None else value,
        )
        selected_rows = [row for row in algorithm_rows if selected_algorithm is None
                         or row["algorithm_name"] == selected_algorithm]
        algorithm_data = pd.DataFrame(selected_rows).rename(columns={
            "algorithm_vendor": "Vendor", "algorithm_name": "Algorithm",
            "ai_processed_studies": "Processed studies",
            "successful_results": "Successful results", "ai_errors": "AI errors",
            "avg_ai_processing_minutes": "AI processing TAT (min)",
            "avg_study_turnaround_minutes": "Study TAT (min)",
        })
        # SQL calculated the averages. Format only for display and keep missing
        # timings distinct from a true zero-minute duration.
        for column in ("AI processing TAT (min)", "Study TAT (min)"):
            algorithm_data[column] = algorithm_data[column].map(
                lambda value: "N/A" if pd.isna(value) else f"{value:.1f}"
            )
        st.dataframe(algorithm_data, hide_index=True)
        st.caption(
            "Successful results are the sample size for AI processing TAT; "
            "processed studies are the sample size for study TAT. "
            "Different tasks and small samples make these unsuitable for ranking products."
        )


if __name__ == "__main__":
    main()
