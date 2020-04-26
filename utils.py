
import base64
import os
from pathlib import Path

import numpy as np
import xarray as xr
from plotly import graph_objs as go

import analysis


def parse_data(contents):
    """
        Function for parsing data from a millimeter-wave
        data file.
    """
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string).decode("utf-8")
    decoded = decoded.split("\r")
    
    settings = dict()
    intensity = list()
    # Boolean flags to check when to start/stop
    # reading parameters
    read_params = False
    read_int = False
    read_zeeman = False
    finished = False
    fieldoff_intensities = list()
    fieldon_intensities = list()
    for line in decoded:
        if "*****" in line:
            read_int = False
            if finished is True:
                break
        if "Scan" in line:
            if "[Field ON]" in line:
                read_zeeman = True
            scan_details = line.split()
            settings["ID"] = int(scan_details[1])
            # settings["Date"] = str(scan_details[4])
            read_params = True
            read_int = False
            continue
        if read_int is True:
            if read_zeeman is False:
                fieldoff_intensities += [float(value) for value in line.split()]
            else:
                fieldon_intensities += [float(value) for value in line.split()]
                finished = True
        if read_params is True and len(line.split()) > 1:
            # Read in the frequency step, frequency, and other info
            # needed to reconstruct the frequency data
            scan_params = line.split()
            shift = 1
            settings["Frequency"] = float(scan_params[0])
            settings["Frequency step"] = float(scan_params[1])
            if len(scan_params) == 4:
                settings["Multiplier"] = 1.
                shift = 0
            # If the multiplier data is there, we don't shift the read
            # index over by one
            else:
                settings["Multiplier"] = float(scan_params[2])
            settings["Center"] = float(scan_params[2 + shift])
            settings["Points"] = int(scan_params[3 + shift])
            read_params = False
            # Start reading intensities immediately afterwards
            read_int = True
            continue
    # convert data to NumPy arrays
    fieldoff_intensities = np.array(fieldoff_intensities)
    fieldon_intensities = np.array(fieldon_intensities)
    # Generate matching arrays for holding FFTs
    fieldoff_fft = np.real(np.fft.fft(fieldoff_intensities))
    if len(fieldon_intensities) > 1:
        fieldon_fft = np.real(np.fft.fft(fieldon_intensities))
        combined = np.real(np.fft.ifft(fieldoff_fft - fieldon_fft))
    else:
        fieldon_fft = np.zeros(fieldon_intensities.size)
        combined = fieldoff_intensities
    # Generate the frequency grid
    settings["Frequency step"] = settings["Frequency step"] * settings["Multiplier"]
    # This calculates the length of either side
    side_length = settings["Frequency step"] * (settings["Points"] // 2)
    start_freq = settings["Frequency"] - side_length
    end_freq = settings["Frequency"] + side_length
    frequency = np.linspace(start_freq, end_freq, settings["Points"])
    # package everything into a Pandas dataframe
    dataset = xr.Dataset(
        {
            "Field OFF": fieldoff_intensities,
            "Field ON": fieldon_intensities,
            "OFF FFT": fieldoff_fft,
            "ON FFT": fieldon_fft,
            "OFF - ON": combined
        },
        coords={"Frequency": frequency, "Index": np.arange(fieldoff_fft.size)},
        attrs=settings
    )
    # serialize pandas dataframe for use
    dataset.to_netcdf("data/uploaded-dataset.nc", engine="h5netcdf", invalid_netcdf=True)
    
    return dataset


def read_serialized_data():
    temp_path = Path("data/uploaded-dataset.nc")
    if temp_path.exists():
        return xr.open_dataset(temp_path)
    else:
        raise Exception("No uploaded data detected.")
    

def clean_serialized():
    for file in Path("data").rglob("*.nc"):
        os.remove(file)


def generate_plot(data=None):
    """
    Function to create the frequency and time domain plots. If no
    data is supplied, we simply use the serialized data.

    Parameters
    ----------
    data : xarray.Dataset, optional
        Data that has key access similar to either Pandas DataFrames
        or xarray Datasets, by default None
    """
    if data is None:
        data = read_serialized_data()
    name = data.attrs.get("ID")
    freq_plot = go.Figure()
    freq_plot.layout = {
        "title": f"Frequency Domain: {name}",
        "xaxis_title": "Frequency (MHz)"
    }
    freq_plot.add_trace(
        go.Scatter(
            x=data["Frequency"],
            y=data["Field OFF"],
            name="Field Off"
        )
    )
    if data["Field ON"].sum() > 0.:
        freq_plot.add_trace(
            go.Scatter(
                x=data["Frequency"],
                y=data["Field ON"],
                name="Field On"
            )
        )
        freq_plot.add_trace(
            go.Scatter(
                x=data["Frequency"],
                y=data["OFF - ON"],
                name="Off - On"
            )
        )
    # do the time domain plot now
    time_plot = go.Figure()
    time_plot.layout = {
        "title": "Time Domain",
        "xaxis_title": "Index"
    }
    for key in ["OFF FFT", "ON FFT"]:
        if data[key].sum() > 0.:
            time_plot.add_trace(
                go.Scatter(
                    x=data["Index"],
                    y=np.real(data[key]),
                    name=key
                )
            )
    return freq_plot, time_plot


def process_signal(json_data: dict, data=None):
    """
    Function called by the application callback to perform
    the FFT filtering. The input of this function comes from
    the JSON data of the Plotly `Figure`, corresponding to the
    x-axis range spanned in the time domain plot.

    Parameters
    ----------
    json_data : dict
        [description]
    data : [type], optional
        [description], by default None

    Returns
    -------
    [type]
        [description]
    """
    if data is None:
        data = read_serialized_data()
    signal = data["OFF - ON"]
    # Get the time domain cut off
    low_cut = int(json_data.get("xaxis.range[0]", 0))
    high_cut = int(json_data.get("xaxis.range[1]", 1e4))
    signal = analysis.filter_signal(signal, low_cut, high_cut)
    # Save the data to disk
    data["OFF - ON"] = signal
    # data.to_netcdf("data/processed-dataset.nc", engine="h5netcdf", invalid_netcdf=True)
    # Now make a plot of it
    processed_plot = go.Figure()
    processed_plot.layout = {
        "title": "Processed Frequency Signal",
        "xaxis_title": "Frequency (MHz)"
    }
    processed_plot.add_trace(
        go.Scatter(
            x=data["Frequency"],
            y=signal,
            name="Processed",
        )
    )
    return processed_plot