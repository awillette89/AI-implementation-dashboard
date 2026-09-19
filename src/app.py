"""A first Streamlit dashboard using the project's existing SQL metrics."""

import sqlite3

import pandas as pd
import streamlit as st

from summarize_metrics import (
    format_value, load_algorithm_turnaround, load_modality_utilization, load_modality_volumes,
    load_error_details, load_overall_metrics, load_sites,
)


def main() -> None:
    # Streamlit builds the page in the same order as these Python statements.
    st.set_page_config(page_title="AI Implementation Dashboard", layout="wide")
    st.title("AI Implementation Dashboard")
    st.caption("Portfolio demo · 500 simulated imaging studies · No patient data")
    st.write(
        "Built for imaging and AI implementation teams to explore adoption, "
        "investigate processing failures, and monitor turnaround time. "
        "Choose a site, then use the tabs to explore its workflow."
    )
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
    # all tab helpers, so changing it updates every tab consistently.
    overview_tab, usage_tab, error_tab, algorithm_tab = st.tabs(
        ["Overview", "AI usage & reliability", "Errors", "Algorithm turnaround"]
    )
    with overview_tab:
        render_overview(metrics, selected_site)
    with usage_tab:
        render_usage(metrics, selected_site)
    with error_tab:
        render_errors(metrics, selected_site)
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



def render_usage(metrics: dict, selected_site: str | None) -> None:
    """Show the existing utilization chart and supporting counts."""
    # These reuse the loaded results, keeping reliability and adoption visible
    # alongside utilization without introducing new calculations.
    error_column, adoption_column = st.columns(2)
    with error_column:
        st.metric("AI errors", format_value(metrics["AI error rate"]["ai_error_rate_percent"], "percent"),
                  help="Processed studies with an error divided by all AI-processed studies.")
    with adoption_column:
        st.metric("AI adoption", format_value(metrics["AI adoption"]["ai_adoption_rate_percent"], "percent"),
                  help="Studies where radiologists used AI divided by studies with an available result.")
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
        # Format percentages only in the table, keeping chart values numeric.
        table_data = utilization_data.copy()
        table_data["AI utilization (%)"] = table_data["AI utilization (%)"].map(
            lambda value: format_value(value, "percent")
        )
        with st.expander("View counts behind the percentages"):
            st.dataframe(table_data, hide_index=True)



def render_errors(metrics: dict, selected_site: str | None) -> None:
    """Show failed studies and explain each simulated failure."""
    st.subheader("Why AI processing failed")
    st.caption(
        "Reasons below are assigned mock scenarios, not findings from real logs "
        "or evidence of vendor defects. These are workflow failures, not diagnostic accuracy errors."
    )
    error_metrics = metrics["AI error rate"]
    count_column, rate_column = st.columns(2)
    with count_column:
        st.metric("Failed studies", format_value(error_metrics["ai_error_studies"], "count"))
    with rate_column:
        st.metric("AI error rate", format_value(error_metrics["ai_error_rate_percent"], "percent"),
                  help="Failed AI-processed studies divided by all AI-processed studies at this site.")
    try:
        errors = load_error_details(selected_site)
    except (OSError, sqlite3.Error) as error:
        st.error(f"Could not load error details: {error}")
        return
    if not errors:
        st.info("No AI processing errors are recorded for this selection.")
        return

    error_data = pd.DataFrame(errors)
    # Count rows by reason. Each failed study appears once in this summary.
    reasons = error_data.groupby("ai_error_reason").size().reset_index(name="Failed studies")
    reasons = reasons.rename(columns={"ai_error_reason": "Mock reason"}).sort_values(
        ["Failed studies", "Mock reason"], ascending=[False, True]
    )
    st.markdown("**Errors by reason**")
    st.dataframe(reasons, hide_index=True)
    st.markdown("**Failed studies**")
    st.caption("Click any cell in a failed study to see its explanation, or use the dropdown.")
    study_ids = [row["study_id"] for row in errors]
    # Separate widget identities for each set of studies prevent a selection
    # from another site from pointing at the wrong row after filtering.
    scope = repr((selected_site, tuple(study_ids)))
    table_key = f"failed_study_cells_{scope}"
    dropdown_key = f"error_lookup_{scope}"
    selected_key = f"selected_error_{scope}"

    def explain_lookup() -> None:
        # Keep the chosen study separately so clearing the search widget does
        # not clear its explanation. The next lookup starts ready for a paste.
        value = st.session_state.get(dropdown_key)
        if value in study_ids:
            st.session_state[selected_key] = value
        st.session_state[dropdown_key] = None

    def explain_selected_row() -> None:
        # Table clicks and dropdown choices update the same selected study.
        cells = st.session_state[table_key]["selection"]["cells"]
        # Each selected cell is (original row position, column name).
        # Single-cell selection avoids the row-selection checkbox column.
        if cells and 0 <= cells[0][0] < len(study_ids):
            st.session_state[selected_key] = study_ids[cells[0][0]]
            st.session_state[dropdown_key] = None

    st.dataframe(error_data.drop(columns="ai_error_detail").rename(columns={
        "study_id": "Study ID", "study_date": "Date", "site": "Site",
        "modality": "Modality", "algorithm_name": "Algorithm",
        "ai_error_reason": "Mock reason",
    }), hide_index=True, key=table_key, on_select=explain_selected_row,
        selection_mode="single-cell")
    # A lookup keeps the full explanation readable without a very wide table.
    st.selectbox(
        "Explain an error", options=study_ids, key=dropdown_key, index=None,
        placeholder="Type or paste a Study ID", on_change=explain_lookup,
        help="Search failed studies at the selected site. Select a matching ID to view its explanation.",
    )
    selected_study = st.session_state.get(selected_key)
    if selected_study not in study_ids:
        st.caption("Click a failed study above, or search for its Study ID here.")
        return
    selected = next(row for row in errors if row["study_id"] == selected_study)
    st.markdown(f"**{selected['study_id']} · {selected['algorithm_name']}**")
    st.write(f"Mock reason: {selected['ai_error_reason']}")
    st.info(selected["ai_error_detail"])


def render_algorithms(selected_site: str | None) -> None:
    """Keep algorithm lookup in its own tab."""
    st.subheader("Simulated algorithm turnaround")
    st.caption(
        "Simulated timings, not vendor benchmarks. AI processing time measures AI "
        "start to successful result. Study turnaround measures study start to "
        "completion among AI-processed studies, including errors."
    )
    with st.expander("About these algorithm examples and sources"):
        st.write(
            "These are real product names paired with invented data, not a ranking "
            "or a head-to-head evaluation. Each study has at most one assigned "
            "algorithm. All products use the same mock timing distributions. "
            "Clinical matching is simplified, and study completion is not changed by AI."
        )
        st.markdown(
            "Official product sources: [Aidoc ICH](https://www.aidoc.com/solutions/neuro/), "
            "[Aidoc PE](https://www.aidoc.com/solutions/vte-solutions/), "
            "[Viz ICH](https://www.viz.ai/indications-for-use), "
            "[Viz PE](https://www.viz.ai/news/new-clinical-data-supports-viz-ai-solution-for-improved-pulmonary-embolism-detection-and-care-coordination), "
            "[Rapid ICH](https://www.rapidai.com/press-release/rapid-platform-expands-to-address-hemorrhagic-stroke), "
            "[Rapid ASPECTS](https://www.rapidai.com/press-release/rapid-aspects-first-neuroimaging-solution-with-cadx-fda-clearance), "
            "[icobrain ms](https://www.icometrix.com/multiple-sclerosis). "
            "Names and broad tasks checked September 18, 2026; no vendor performance claims imported."
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
        # This dropdown affects only the algorithm detail cards. The Site dropdown
        # above still limits the data for the entire page.
        selected_algorithm = st.selectbox(
            "Look up an algorithm",
            options=[None, *sorted(row["algorithm_name"] for row in algorithm_rows)],
            format_func=lambda value: "All algorithms" if value is None else value,
        )
        if selected_algorithm is not None:
            selected = next(row for row in algorithm_rows
                            if row["algorithm_name"] == selected_algorithm)
            st.markdown(f"**{selected_algorithm} · {selected['algorithm_vendor']}**")
            processing_column, study_column = st.columns(2)
            with processing_column:
                st.metric("AI processing TAT", format_value(selected["avg_ai_processing_minutes"], "minutes"),
                          help="Average AI start to result, using successful results only.")
                st.caption(f"Based on {selected['successful_results']} successful results")
            with study_column:
                st.metric("Study TAT", format_value(selected["avg_study_turnaround_minutes"], "minutes"),
                          help="Average study start to completion among processed studies, including errors.")
                st.caption(f"Based on {selected['ai_processed_studies']} processed studies")
        else:
            st.caption("Select an algorithm for its timing cards, or compare all algorithms below.")

        st.markdown("**Compare algorithms at this site**")
        # Retain the comparison table when a product is selected, so users can
        # see its context without repeatedly changing the dropdown.
        algorithm_data = pd.DataFrame(algorithm_rows).sort_values("algorithm_name").rename(columns={
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
