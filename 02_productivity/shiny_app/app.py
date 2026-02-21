# app.py
# NYT Most Popular Articles - Shiny App
# A Python Shiny app that queries the New York Times Most Popular API
# and displays results in a modern sidebar + table layout.
# Jimmy

# This app wraps the existing NYT API query logic (from query_nyapi.py)
# into an interactive web interface. Users can select endpoint type,
# time period, and filter by date range, then view results as a
# formatted table or expandable JSON.

# 0. Setup #################################

## 0.1 Load Packages ############################

from shiny import App, ui, render, reactive  # Shiny core framework
import pandas as pd       # for building the results table
import json               # for JSON display
from datetime import datetime, timedelta, date  # for date handling
import os                 # for path resolution

# Import our custom NYT API helper module
from nyt_api import fetch_articles, get_api_key, NYTApiError, VALID_ENDPOINTS, VALID_PERIODS

# 1. UI Definition #################################

# Build the sidebar with input controls
app_sidebar = ui.sidebar(
    # App title / branding in sidebar
    ui.h4("NYT Popular Articles"),
    ui.hr(),

    # Endpoint selector: Most Viewed, Emailed, or Shared
    ui.input_select(
        id="endpoint",
        label="Article Type",
        choices=VALID_ENDPOINTS,  # {"viewed": "Most Viewed", ...}
        selected="viewed"
    ),

    # Period selector: 1, 7, or 30 days (maps to API period param)
    ui.input_select(
        id="period",
        label="Popularity Period",
        choices={"1": "Past 1 Day", "7": "Past 7 Days", "30": "Past 30 Days"},
        selected="1"
    ),

    # Number of articles to fetch (1-20)
    ui.input_slider(
        id="num_articles",
        label="Number of Articles",
        min=1, max=20, value=20, step=1
    ),

    ui.hr(),

    # Date range filter (client-side filter on published_date)
    ui.input_date_range(
        id="date_range",
        label="Filter by Published Date",
        start=(date.today() - timedelta(days=30)),
        end=date.today()
    ),

    ui.hr(),

    # Search button triggers the API query
    ui.input_action_button(
        id="search",
        label="Search",
        class_="btn-primary w-100"
    ),

    # Status / error message area
    ui.output_ui("status_message"),

    width=320,
)

# Build the main content area with tabbed views
app_main = ui.navset_card_tab(
    # Tab 1: Articles displayed as a data table
    ui.nav_panel(
        "Articles Table",
        ui.output_data_frame("results_table")
    ),
    # Tab 2: Raw JSON in an expandable accordion
    ui.nav_panel(
        "JSON View",
        ui.output_ui("json_view")
    ),
)

# Combine sidebar and main area into the full page
app_ui = ui.page_sidebar(
    app_sidebar,
    # Page header
    ui.h2("New York Times Most Popular Articles"),
    ui.p(
        "Query the NYT Most Popular API to browse trending articles. "
        "Select your parameters in the sidebar and click Search.",
        class_="text-muted"
    ),
    app_main,
    title="NYT Popular Articles",
    fillable=True,
)


# 2. Server Logic #################################

def server(input, output, session):
    """Server function: handles reactivity, API calls, and rendering."""

    # Reactive value to store fetched articles (list of dicts)
    articles_data = reactive.value(None)
    # Reactive value to store error/status messages
    error_msg = reactive.value(None)
    # Reactive value to track loading state
    is_loading = reactive.value(False)

    # Check if API key is available on startup (loads from .env at project root)
    api_key = get_api_key()

    ## 2.1 Fetch data when Search is clicked ################

    @reactive.effect
    @reactive.event(input.search)
    def _fetch_data():
        """Triggered when user clicks the Search button.
        Calls the NYT API and stores results or error messages."""
        is_loading.set(True)
        error_msg.set(None)
        articles_data.set(None)

        try:
            # Call our API helper with the user's selected parameters
            articles = fetch_articles(
                endpoint=input.endpoint(),
                period=int(input.period()),
                num_articles=input.num_articles(),
                api_key=api_key
            )
            articles_data.set(articles)
            error_msg.set(None)

        except NYTApiError as e:
            # Known API errors get a friendly message
            error_msg.set(str(e))
            articles_data.set(None)

        except Exception as e:
            # Unexpected errors
            error_msg.set(f"An unexpected error occurred: {str(e)}")
            articles_data.set(None)

        finally:
            is_loading.set(False)

    ## 2.2 Filter articles by date range ####################

    @reactive.calc
    def filtered_articles():
        """Apply the client-side date range filter to fetched articles.
        The NYT API only supports fixed periods (1/7/30 days), so this
        lets users narrow results to a specific date window."""
        data = articles_data.get()
        if data is None:
            return None

        start_date, end_date = input.date_range()

        filtered = []
        for article in data:
            try:
                pub_date = datetime.strptime(article["published_date"], "%Y-%m-%d").date()
                if start_date <= pub_date <= end_date:
                    filtered.append(article)
            except (ValueError, KeyError):
                # If date parsing fails, include the article anyway
                filtered.append(article)

        return filtered

    ## 2.3 Render the status / error message ################

    @render.ui
    def status_message():
        """Display status or error messages below the Search button."""
        msg = error_msg.get()
        data = filtered_articles()

        if is_loading.get():
            return ui.div(
                ui.p("Fetching articles...", class_="text-info"),
                class_="mt-3"
            )

        if msg:
            return ui.div(
                ui.div(msg, class_="alert alert-danger mt-3", role="alert"),
            )

        if data is not None:
            total = len(articles_data.get()) if articles_data.get() else 0
            shown = len(data)
            return ui.div(
                ui.div(
                    f"Showing {shown} of {total} articles fetched.",
                    class_="alert alert-success mt-3",
                    role="alert"
                ),
            )

        return ui.div()  # empty when no action yet

    ## 2.4 Render the Articles Table ########################

    @render.data_frame
    def results_table():
        """Render filtered articles as a DataTable with key columns."""
        data = filtered_articles()
        if not data:
            return pd.DataFrame(columns=["Title", "Date", "Section", "Abstract", "People", "URL"])

        # Build a pandas DataFrame for display
        display_df = pd.DataFrame({
            "Title": [a["title"] for a in data],
            "Date": [a["published_date"] for a in data],
            "Section": [a["section"] for a in data],
            "Abstract": [a["abstract"] for a in data],
            "People": [a["per_facet"] for a in data],
            "URL": [a["url"] for a in data],
        })

        return render.DataTable(display_df, width="100%", height="100%")

    ## 2.5 Render the JSON View #############################

    @render.ui
    def json_view():
        """Render the raw article data as expandable JSON.
        Each article is wrapped in an accordion panel so users
        can expand individual articles to inspect all fields."""
        data = filtered_articles()
        if not data:
            return ui.div(
                ui.p("No data to display. Click Search to fetch articles.",
                     class_="text-muted p-3"),
            )

        # Build an accordion with one panel per article
        panels = []
        for i, article in enumerate(data):
            # Use title as the accordion header
            header = f"{i+1}. {article['title']} ({article['published_date']})"

            # Build a clean JSON representation (include list facets)
            json_data = {
                "title": article["title"],
                "published_date": article["published_date"],
                "section": article["section"],
                "url": article["url"],
                "abstract": article["abstract"],
                "descriptors": article["des_facet_list"],
                "people": article["per_facet_list"],
                "organizations": article["org_facet_list"],
                "locations": article["geo_facet_list"],
            }
            json_str = json.dumps(json_data, indent=2, ensure_ascii=False)

            panels.append(
                ui.accordion_panel(
                    header,
                    ui.pre(json_str, style="max-height: 400px; overflow-y: auto;"),
                )
            )

        return ui.accordion(*panels, id="json_accordion", open=False)


# 3. Create App #################################

# Combine UI and server into the Shiny App object
app = App(app_ui, server)


# 4. Run for deployment #################################
# When the platform runs `python app.py`, this keeps the server running
# and binds to 0.0.0.0:PORT so the app is reachable from outside.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

