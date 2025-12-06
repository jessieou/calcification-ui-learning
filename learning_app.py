import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
from skimage import io
import os
import csv
from datetime import datetime

# -----------------------------
# 1) Load CSV data at startup
# -----------------------------
# Now using learning_cases.csv with new schema
cases_df = pd.read_csv("learning_cases.csv")

# Rename columns so the rest of the code can stay the same
cases_df = cases_df.rename(columns={
    "Order": "case_id",              # used as the main case identifier
    "ID": "id",              # optional, not currently used in UI
    "Age": "patient_age",
    "Race": "patient_race",
    "Ethnicity": "patient_ethnicity",
    "Size (mm)": "calcification_span",
    "Pathology": "correct_pathology",
    "BI-RADS": "correct_BIRADS"
})

def get_case_row(case_id):
    row = cases_df.loc[cases_df["case_id"] == int(case_id)]
    if row.empty:
        return None
    return row.iloc[0]

def get_next_case_id(current_case_id):
    current_idx = cases_df.index[cases_df["case_id"] == int(current_case_id)]
    if len(current_idx) == 0:
        return str(cases_df["case_id"].iloc[0])
    idx = current_idx[0]
    next_idx = idx + 1
    if next_idx < len(cases_df):
        return str(cases_df["case_id"].iloc[next_idx])
    else:
        return str(cases_df["case_id"].iloc[0])

def get_start_case_for_user(user_id):
    """
    Look at <user_id>_learning.csv and decide which case_id
    the user should start on this session.

    Returns:
        str case_id to start at, or None if the user has completed all cases.
    """
    filename = f"output/{user_id}_learning.csv"
    # Debug: see what the app thinks
    print("get_start_case_for_user:", user_id, "-> looking for", filename)
    # If the user has never logged in / no file yet, start at the first case
    if not os.path.exists(filename):
        return str(cases_df["case_id"].iloc[0])

    try:
        progress_df = pd.read_csv(filename)
    except Exception:
        # If the file is unreadable for some reason, fall back to the first case
        return str(cases_df["case_id"].iloc[0])

    if progress_df.empty or "case_id" not in progress_df.columns:
        return str(cases_df["case_id"].iloc[0])

    # Get the last completed case_id (assumes they submit in order)
    completed_case_ids = (
        progress_df["case_id"]
        .dropna()
        .astype(int)
        .unique()
    )
    if len(completed_case_ids) == 0:
        return str(cases_df["case_id"].iloc[0])

    last_case = int(completed_case_ids.max())
    print("Last completed case:", last_case)

    # Find where that case sits in cases_df
    current_idx = cases_df.index[cases_df["case_id"] == last_case]
    if len(current_idx) == 0:
        # If something weird, just restart at first
        return str(cases_df["case_id"].iloc[0])

    idx = current_idx[0]

    # If they’ve already done the last case, there is nothing left
    if idx == len(cases_df) - 1:
        return None

    # Otherwise, start at the next case
    return str(cases_df["case_id"].iloc[idx + 1])

# Helper mappings for display
RACE_MAP = {
    "B": "Black",
    "A": "Asian",
    "W": "White",
}

ETHNICITY_MAP = {
    "NH": "Not Hispanic",
    "H": "Hispanic",
}


def pretty_race(code):
    if pd.isna(code):
        return "Unknown"
    code = str(code).strip()
    return RACE_MAP.get(code, code)  # fall back to the raw code if unmapped


def pretty_ethnicity(code):
    if pd.isna(code):
        return "Unknown"
    code = str(code).strip()
    return ETHNICITY_MAP.get(code, code)

# -----------------------------
# 2) Image loading utilities
# -----------------------------
def load_imgs(case_id):
    """
    Load the CC and ML images for a given case ID.

    We assume:
      case_id = 1  -> images/L001CC.png and images/L001ML.png
      case_id = 2  -> images/L002CC.png and images/L002ML.png
      ...
    where `case_id` comes from the `Index` column in learning_cases.csv.
    """
    base_path = "images/learning_cases"

    # case_id should be an integer (from the Index column)
    idx = int(case_id)
    case_str = f"L{idx:03d}"   # 1 -> "L001", 2 -> "L002", etc.

    cc_path = os.path.join(base_path, f"{case_str}CC.png")
    ml_path = os.path.join(base_path, f"{case_str}ML.png")

    if not os.path.exists(cc_path):
        raise FileNotFoundError(f"Cannot find CC image for case {case_id}: {cc_path}")
    if not os.path.exists(ml_path):
        raise FileNotFoundError(f"Cannot find ML image for case {case_id}: {ml_path}")

    img_cc = io.imread(cc_path)
    img_ml = io.imread(ml_path)

    # Keep the same return order you were using before:
    # let's treat CC as the "full-field" image and ML as the ROI
    return img_cc, img_ml

def create_image_fig(image):
    fig = px.imshow(image)
    fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
    fig.update_xaxes(showticklabels=False).update_yaxes(showticklabels=False)
    return fig

# -----------------------------
# 3) Dash App setup
# -----------------------------
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc_css],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True
)
app.title = "Mammo UI"

# -----------------------------
# Login Page
# -----------------------------
def login_page():
    return html.Div([
        html.H2("Enter your ID", style={"fontSize": "72px", "color": "white", "marginTop": "100px", "marginLeft": "900px"}),
        dcc.Input(id="user-id-input", type="text", placeholder="", style={"fontSize": "40px", "marginLeft": "900px"}),
        html.Br(), html.Br(),
        dbc.Button("Login", id="login-button", color="primary", n_clicks=0, style={'font-size': '40px', 
                                                                                   'textAlign': 'center', 
                                                                                   'marginLeft': '900px',
                                                                                   'width': '300px'}),
        html.Br(), html.Div(id="login-message", style={"color": "red",
                                                       "fontSize": "40px",
                                                       "marginTop": "10px",
                                                       "marginLeft": "900px"})

    ])

# -----------------------------
# Thank You End Screen
# -----------------------------
def thank_you_page():
    return html.Div(
        [
            html.H1(
                "You have completed all learning cases.",
                style={
                    "fontSize": "64px",
                    "color": "white",
                    "textAlign": "center",
                    "marginBottom": "20px",
                },
            ),
            html.H1(
                "Thank you for your participation!",
                style={
                    "fontSize": "64px",
                    "color": "white",
                    "textAlign": "center",
                    "marginBottom": "20px",
                },
            ),
        ],
        style={
            "backgroundColor": "black",
            "height": "100vh",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "alignItems": "center",
        },
    )

# -----------------------------
# Main App UI Components
# -----------------------------
# The feedback modal
feedback_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            html.H4("Answer Feedback", className="mb-0", style={"fontSize": "2rem"})
        ),
        dbc.ModalBody(
            html.Div(id="feedback-message", style={"fontSize": "2rem", "lineHeight": "2"})
        ),
        dbc.ModalFooter(
            dbc.Button(
                "Close",
                id="close-feedback",
                className="ml-auto",
                n_clicks=0,
                style={"fontSize": "1.1rem", "padding": "0.5rem 1.25rem"}
            )
        ),
    ],
    id="feedback-modal",
    is_open=False,
    size="lg",      # Makes the window bigger
    backdrop=False,
    fade=False,
    style={"padding": "1rem"}  # Optional: extra spacing inside the modal
)

# Interval for auto-close after 3 seconds
auto_close_interval = dcc.Interval(
    id='auto-close-interval',
    interval=2000,   # 3 seconds
    n_intervals=0,
    disabled=True,
    max_intervals=1  # fire once each time it's enabled
)

# dynamically build layout 
config = {"scrollZoom": True, "displayModeBar": True, "displaylogo": False}

def build_main_layout(start_case_id):
    # Look up the row for the starting case
    row = get_case_row(start_case_id)
    if row is None:
        # Fallback: if something's wrong, just show the first case
        row = get_case_row(1)

    # Load images for this case
    img1, img2 = load_imgs(row["case_id"])
    fig1 = create_image_fig(img1)
    fig2 = create_image_fig(img2)

    # Graphs for CC / ML
    full_field_graph = dcc.Graph(
        id="graph-px",
        figure=fig1,
        config=config,
        style={"height": "100vh"},
    )
    ROI_graph = dcc.Graph(
        id="roi-px",
        figure=fig2,
        config=config,
        style={"height": "100vh"},
    )

    # Labeled containers
    cc_image_block = html.Div(
        [
            html.Div(
                "CC mag",
                style={
                    "textAlign": "center",
                    "fontSize": "30px",
                    "color": "white",
                    "marginBottom": "10px",
                },
            ),
            full_field_graph,
        ]
    )
    ml_image_block = html.Div(
        [
            html.Div(
                "ML mag",
                style={
                    "textAlign": "center",
                    "fontSize": "30px",
                    "color": "white",
                    "marginBottom": "10px",
                },
            ),
            ROI_graph,
        ]
    )

    # Info card, initialized with this case's data
    info_card = dbc.Card(
        [
            dbc.CardBody(
                [
                    html.P(
                        f"Case ID: {row['id']}",
                        id="case-id-label",
                        style={"font-size": "30px", "color": "white"},
                    ),
                    html.P(
                        f"Patient age: {row['patient_age']}",
                        id="patient-age-label",
                        style={"font-size": "30px", "color": "white"},
                    ),
                    html.P(
                        f"Patient race: {pretty_race(row['patient_race'])}",
                        id="patient-race-label",
                        style={"font-size": "30px", "color": "white"},
                    ),
                    html.P(
                        f"Patient ethnicity: {pretty_ethnicity(row['patient_ethnicity'])}",
                        id="patient-ethnicity-label",
                        style={"font-size": "30px", "color": "white"},
                    ),
                    html.P(
                        f"Calcification longest span (mm): {row['calcification_span']}",
                        id="calc-span-label",
                        style={"font-size": "30px", "color": "white"},
                    ),
                    html.P(
                        "Given the CC and ML mag views, what BI-RADS final assessment category would you give these calcifications?",
                        style={"font-size": "30px", "color": "white"},
                    ),
                    dcc.RadioItems(
                        id="input-birads",
                        options=["BI-RADS 2", "BI-RADS 3", "BI-RADS 4"],
                        value=None,
                        labelStyle={
                            "display": "block",
                            "font-size": "30px",
                            "color": "white",
                        },
                    ),
                    html.P(
                        "Based on the imaging appearance, what do you think the most likely etiology of these calcifications are?",
                        style={
                            "font-size": "30px",
                            "color": "white",
                            "marginTop": "20px",
                        },
                    ),
                    dcc.RadioItems(
                        id="input-pathology",
                        options=["Benign", "Atypia", "DCIS", "Invasive"],
                        value=None,
                        labelStyle={
                            "display": "block",
                            "font-size": "30px",
                            "color": "white",
                        },
                    ),
                    html.Br(),
                    html.P(
                        "How confident are you in your assessment? (%)",
                        style={"font-size": "30px", "color": "white"},
                    ),
                    dcc.Slider(
                        id="input-confidence",
                        min=0,
                        max=100,
                        value=None,
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                    html.Br(),
                    dbc.Button(
                        "Submit & Next",
                        id="submit-button",
                        n_clicks=0,
                        style={
                            "font-size": "26px",
                            "marginTop": "20px",
                            "width": "100%",
                            "background-color": "black",
                            "color": "white",
                            "border": "2px solid white",
                        },
                    ),
                ]
            )
        ],
        style={
            "background-color": "black",
            "border": "1px solid white",
            "padding-top": "20px",
        },
    )

    # Hidden case id & previous-case store seeded with the start_case_id
    hidden_case_id = html.Div(
        id="case-id",
        children=str(start_case_id),
        style={"display": "none"},
    )

    return html.Div(
        style={
            "display": "flex",
            "justify-content": "space-between",
            "background-color": "black",
            "color": "black",
            "height": "100vh",
        },
        children=[
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(cc_image_block, width=4),
                            dbc.Col(ml_image_block, width=4),
                            dbc.Col(info_card, width=4),
                        ],
                        justify="between",
                    ),
                    hidden_case_id,
                    dcc.Store(id="previous-case-id", data=str(start_case_id)),
                    feedback_modal,
                    auto_close_interval,
                ],
                fluid=True,
            )
        ],
    )

# -----------------------------
# App layout that switches views
# -----------------------------
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="session", storage_type="session"),
    dcc.Store(id="finished", storage_type="session", data=False),  # <-- NEW
    html.Div(id="page-content")
])


# -----------------------------
# Login Logic
# -----------------------------
@app.callback(
    Output("session", "data"),
    Output("login-message", "children"),
    Input("login-button", "n_clicks"),
    State("user-id-input", "value"),
    prevent_initial_call=True
)
def handle_login(n_clicks, user_input):
    if not user_input:
        return dash.no_update, ""
    with open("valid_ids.csv") as f:
        valid_ids = set(line.strip() for line in f)
    user_id = user_input.strip()
    if user_id in valid_ids:
        filename = f"output/{user_id}_learning.csv"
        # Only create the file with header if it does NOT already exist
        if not os.path.exists(filename):
            with open(filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "userID",
                    "timestamp",
                    "case_id",
                    "patient_id",
                    "pathology",
                    "birads",
                    "confidence"
                ])
        return user_id, ""
    else:
        return dash.no_update, "Invalid ID."

# -----------------------------
# Page Switching
# -----------------------------
@app.callback(
    Output("page-content", "children"),
    Input("session", "data"),
    Input("finished", "data")   # <-- thank you screen trigger
)
def display_page(user_id, finished):
    if not user_id:
        return login_page()
    # If this session has already marked them finished, show thank-you
    if finished:
        return thank_you_page()
    # Otherwise, compute where this user should start
    start_case_id = get_start_case_for_user(user_id)
    print("display_page for user:", user_id, "start_case_id:", start_case_id)

    # If None, they have already completed all learning cases
    if start_case_id is None:
        return thank_you_page()
    
    # Build main layout starting at the appropriate case
    return build_main_layout(start_case_id)



@app.callback(
    [
        Output("feedback-modal", "is_open"),          # open/close the modal
        Output("feedback-message", "children"),       # feedback text
        Output("case-id", "children"),                # next case ID
        Output("auto-close-interval", "disabled"),    # enable or disable the 3s timer
        Output("auto-close-interval", "n_intervals"), # reset the timer if needed
        Output("finished", "data"),                   # know when to show thank-you screen   
    ],
    [
        Input("submit-button", "n_clicks"),
        Input("close-feedback", "n_clicks"),
        Input("auto-close-interval", "n_intervals"),
    ],
    [
        State("session", "data"),                     # this holds the logged-in user_id
        State("input-pathology", "value"),
        State("input-birads", "value"),
        State("input-confidence", "value"),  # <-- Add this line to capture confidence
        State("case-id", "children"),
        State("feedback-modal", "is_open")
    ]
)
def manage_modal_and_next_case(submit_n_clicks, close_n_clicks, intervals, session_user_id,
                               user_pathology, user_birads, user_confidence,
                               case_id, is_open):
    """
    Single callback that handles:
    1) Submit => open modal with feedback, set next case
    2) Close => close modal
    3) Timer => close modal after 3s
    """

    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    # Ignore the very first call where nothing has been clicked yet to prevent warning trigger on initial login
    submit_n_clicks = submit_n_clicks or 0
    close_n_clicks = close_n_clicks or 0
    intervals = intervals or 0
    if submit_n_clicks == 0 and close_n_clicks == 0 and intervals == 0:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # default no changes
    new_is_open = is_open
    new_msg = dash.no_update
    new_case_id = case_id
    new_disabled = True       # default: timer disabled
    new_n_intervals = intervals
    new_finished = dash.no_update

    if button_id == "submit-button":
        # Submit => check valid, evaluate user answer, open the modal, start the timer
        # Require ALL THREE: pathology, BI-RADS, and confidence
        if (user_pathology is None) and (user_birads is None) and (user_confidence is None):
            new_msg = dbc.Alert(
                "Please answer all questions (BI-RADS, pathology, and confidence) before submitting.",
                color="warning"
            )
            new_is_open = True
            new_disabled = False
            new_n_intervals = 0
            return new_is_open, new_msg, new_case_id, new_disabled, new_n_intervals, new_finished
        elif user_pathology is None:
            new_msg = dbc.Alert("Please answer the pathology question.", color="warning")
            new_is_open = True
            new_disabled = False
            new_n_intervals = 0
            return new_is_open, new_msg, new_case_id, new_disabled, new_n_intervals, new_finished
        elif user_birads is None:
            new_msg = dbc.Alert("Please answer the BI-RADS question.", color="warning")
            new_is_open = True
            new_disabled = False
            new_n_intervals = 0
            return new_is_open, new_msg, new_case_id, new_disabled, new_n_intervals, new_finished
        elif user_confidence is None:
            new_msg = dbc.Alert("Please provide your confidence level before submitting.", color="warning")
            new_is_open = True
            new_disabled = False
            new_n_intervals = 0
            return new_is_open, new_msg, new_case_id, new_disabled, new_n_intervals, new_finished

    
        row = get_case_row(case_id)
        if row is None:
            new_msg = dbc.Alert("No data found for this case.", color="warning")
            new_is_open = True
            new_disabled = False  # enable timer
            new_n_intervals = 0   # reset so it starts counting from 0
        else:
            # Save the user submission to a user-specific CSV file:
            # e.g., for user_id "jjj" -> "jjj_learning.csv"
            timestamp = datetime.now().isoformat()
            patient_id = row["id"]

            if not session_user_id:
                # Safety: if somehow no user is logged in, don't write
                session_user_id = "unknown"

            filename = f"output/{session_user_id}_learning.csv"
            file_exists = os.path.isfile(filename)

            with open(filename, "a", newline="") as csvfile:
                writer = csv.writer(csvfile)
                # If this is a new file, write the header first
                if not file_exists:
                    writer.writerow([
                        "userID",
                        "timestamp",
                        "case_id",
                        "patient_id",
                        "pathology",
                        "birads",
                        "confidence",
                    ])

                confidence_str = f"{user_confidence}%" if user_confidence is not None else ""
                writer.writerow([
                    session_user_id,
                    timestamp,
                    case_id,
                    patient_id,
                    user_pathology,
                    user_birads,
                    confidence_str,
                ])
            correct_pathology = row["correct_pathology"]
            path_result = "✅ Pathology correct." if user_pathology == correct_pathology else f"❌ Pathology incorrect. Correct: {correct_pathology}."
            # learning_cases.csv now stores BI-RADS as numbers like 2, 3, 4
            # but the radio buttons use labels like "BI-RADS 2", "BI-RADS 3", ...
            correct_birads_num = str(row["correct_BIRADS"]).strip()   # "2", "3", "4", ...
            correct_birads = f"BI-RADS {correct_birads_num}"          # "BI-RADS 2", etc.
            birads_result = (
                "✅ BI-RADS correct."
                if user_birads == correct_birads
                else f"❌ BI-RADS incorrect. Correct: {correct_birads}."
            )

            new_msg = html.Div([
                html.P(birads_result),
                html.P(path_result)
            ])
            # Determine if this is the last case
            current_idx = cases_df.index[cases_df["case_id"] == int(case_id)]
            is_last_case = (
                len(current_idx) > 0 and current_idx[0] == len(cases_df) - 1
            )
            if is_last_case:
                # Don't advance to a new case; mark finished instead
                new_case_id = case_id      # or leave as-is
                new_finished = True        # <-- tell the app we're done
            else:
                # Move to next case
                new_case_id = get_next_case_id(case_id)

            # Show modal, start timer
            new_is_open = True
            new_disabled = False  # start the 3s countdown
            new_n_intervals = 0

    elif button_id == "close-feedback":
        # Close => user pressed the "Close" button
        new_is_open = False
        new_disabled = True  # stop the timer

    elif button_id == "auto-close-interval":
        # Timer fired => close the modal automatically
        # but only if intervals > 0 and the modal is open
        if intervals > 0 and is_open:
            new_is_open = False
            new_disabled = True
            new_n_intervals = 0  # reset the timer for next time
    return new_is_open, new_msg, new_case_id, new_disabled, new_n_intervals, new_finished

# -----------------------------
# Update displayed text/images whenever case-id changes
# -----------------------------
@app.callback(
    [
        Output("case-id-label", "children"),
        Output("patient-age-label", "children"),
        Output("patient-race-label", "children"),
        Output("patient-ethnicity-label", "children"),
        Output("calc-span-label", "children"),
        Output("input-pathology", "value"),
        Output("input-birads", "value"),
        Output("graph-px", "figure"),
        Output("roi-px", "figure"),
        Output("input-confidence", "value"),  # <-- This resets the slider
        Output("previous-case-id", "data")
    ],
    Input("case-id", "children"),
    # These maintains the users' inputs if they haven't completed both questions
    [
        State("input-pathology", "value"),
        State("input-birads", "value"),
        State("input-confidence", "value"),
        State("previous-case-id", "data")
    ]
)
def update_case_display(case_id, current_pathology, current_birads, current_confidence, previous_case_id):
    row = get_case_row(case_id)
    if row is None:
        return (
            "Case ID: ???",
            "Patient age: ???",
            "Patient race: ???",
            "Patient ethnicity: ???",
            "Calcification longest span: ???",

            # Return current values instead of resetting
            current_pathology,
            current_birads,
            {},
            {},
            current_confidence,
            previous_case_id
        )

    case_id_text = f"Case ID: {row['id']}"
    age_text = f"Patient age: {row['patient_age']}"
    race_text = f"Patient race: {pretty_race(row['patient_race'])}"
    ethnicity_text = f"Patient ethnicity: {pretty_ethnicity(row['patient_ethnicity'])}"
    span_text = f"Calcification longest span (mm): {row['calcification_span']}"

    img1, img2 = load_imgs(row["case_id"])
    fig1 = create_image_fig(img1)
    fig2 = create_image_fig(img2)

    if case_id != previous_case_id:
        return (
            case_id_text,
            age_text,
            race_text,
            ethnicity_text,
            span_text,
            None,  # reset pathology
            None,  # reset BI-RADS
            fig1,
            fig2,
            None,   # reset confidence
            case_id
        )
    else:
        return (
            case_id_text,
            age_text,
            race_text,
            ethnicity_text,
            span_text,
            current_pathology,
            current_birads,
            fig1,
            fig2,
            current_confidence,
            previous_case_id
        )


if __name__ == '__main__':
    #app.run_server(debug=True)
    # to run locally
    app.run(debug=True, host="127.0.0.1", port=8053)