
import json
import flask
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as gobs

import analysis, utils

external_stylesheets = [
    "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css",
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
                html.P("You can adjust the region to use for the cut-off by simply zooming in the time-domain panel.")
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
        )
    ]
)

if __name__ == "__main__":
    utils.clean_serialized()
    app.run_server(debug=True)
