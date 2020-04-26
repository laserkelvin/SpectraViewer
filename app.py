
import json
import flask
import dash
import dash_table
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as gobs

import analysis, utils

external_stylesheets = [
    "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css",
    "https://fonts.googleapis.com/css2?family=Open+Sans&family=Roboto&display=swap"
]


external_scripts = [
    "https://code.jquery.com/jquery-3.2.1.slim.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js",
    "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js",
]

# Server definition

server = flask.Flask(__name__)
app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    external_scripts=external_scripts,
    server=server,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

# HEADER
# ======

header = dbc.NavbarSimple(
    children=[dbc.NavItem(dbc.NavLink("Main", href="#")),],
    brand="SpectraViewer",
    brand_href="#",
    color="primary",
    dark=True,
)


# COMPONENTS
# ==========

# Your components go here.


# INTERACTION
# ===========

"""
Callback for upload/plotting data.
"""
@app.callback(
    [Output("frequency-plot", "figure"), Output("time-plot", "figure")],
    [Input("upload-data", "contents")]
    )
def uploaded_data(content=None):
    if content is not None:
        df = utils.parse_data(content)
        freq_plot, time_plot = utils.generate_plot(df)
        return freq_plot, time_plot
    else:
        raise dash.exceptions.PreventUpdate


"""
Callback for filtering the time-domain signal, using the user's field of
view as the cutoffs.
"""
@app.callback(
    Output("processed-plot", "figure"),
    [Input("time-plot", "relayoutData")]
)
def update_signal_filter(relayout_data: dict):
    try:
        freq_plot = utils.process_signal(relayout_data)
        return freq_plot
    except:
        raise dash.exceptions.PreventUpdate
    
"""
Peak picking callback
"""
@app.callback(
    Output("output-table", "data"),
    [Input("processed-plot", "clickData")],
    [State("output-table", "data")]
)
def pick_a_peak(click_data, rows):
    if click_data is not None:
        extract_info = click_data["points"][0]
        frequency = extract_info.get("x")
        intensity = extract_info.get("y")
        data = utils.read_serialized_data()
        name = data.attrs.get("ID")
        # Add the data to the Datatable
        rows.append(
            {"scan-num": name,
             "peak-freq": f"{frequency:.4f}",
             "peak-int": f"{intensity:.4f}"
             }
        )
        return rows
    else:
        raise dash.exceptions.PreventUpdate
    
"""
DataTable saving
"""
@app.callback(
    Output("hidden", "children"),
    [Input("save-button", "n_clicks")],
    [State("output-table", "data")]
)
def export_table(n_clicks=0, rows=None):
    if n_clicks:
        utils.save_datatable(rows)
    else:
        raise dash.exceptions.PreventUpdate


# APP LAYOUT
# ==========

app.layout = html.Div(
    [
        header,
        html.Div(
            children=[
                html.H2("Instructions"),
                html.P("SpectraViewer is a Dash application for viewing legacy millimeter-wave data."),
                html.P("Simply upload your data with the browser below, and it should display the frequency/time domain spectra."),
                html.P("The only tweak for the filtering conditions is the cut-off region in the time domain spectrum."),
                html.P("You can adjust the region to use for the cut-off by simply zooming in the time-domain panel."),
                html.P("On the Processed Signal panel, you can click anywhere to record the corresponding frequency; please use this to pick peaks."),
                html.P("Once you're done with analysis, there is Save table button at the bottom of the page to dump the table to a CSV file."),
                html.P("Persistent data is saved in the `data/` folder.")
            ]
        ),
        dcc.Upload(
            id="upload-data",
            children=html.Div(["Drag and Drop, or ", html.A("Select Files.")]),
        ),
        html.H2("Spectra viewport"),
        # this is two plots shown next to one another
        html.Div(
            children=[
                html.Div(
                    className="plot_row",
                    children=[
                        dcc.Graph(
                            id="frequency-plot"
                        )
                    ],
                ),
                html.Div(
                    className="plot_row",
                    children=[
                        dcc.Graph(
                            id="time-plot"
                        )
                    ],
                ),
                html.Div(
                    className="plot_row",
                    children=[
                        dcc.Graph(
                            id="processed-plot"
                        )
                    ],
                )
            ],
            id="plot-div",
        ),
        dash_table.DataTable(
            id="output-table",
            columns=(
                [{"name": "Scan Number", "id": "scan-num", "deletable": True, "renamable": True}, 
                 {"name": "Frequency", "id": "peak-freq", "deletable": True, "renamable": True}, 
                 {"name": "Intensity", "id": "peak-int", "deletable": True, "renamable": True}]
            ),
            data=[{"scan-num": " ", "peak-freq": " ", "peak-int": " "}],
            editable=True,
            row_deletable=True
        ),
        html.Button("Save table", id="save-button"),
        html.Div(id="hidden", children=[])
    ],
    id="top-container"
)

if __name__ == "__main__":
    utils.clean_serialized()
    app.run_server(debug=True)
