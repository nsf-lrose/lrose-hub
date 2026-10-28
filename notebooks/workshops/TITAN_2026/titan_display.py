"""Plot one TITAN complex track on a reflectivity time slider.

The functions here support ``Titan_tutorial_with_display.ipynb``. The notebook
keeps the tutorial narrative; this module holds the plotting code.

Storm outlines use TITAN's native polygon. Each record stores 72 ray lengths,
one every 5 degrees, starting at north and proceeding clockwise. A vertex is

    x = VolCentroidX + radius * sin(angle)
    y = VolCentroidY + radius * cos(angle)

with ``angle`` in radians. ``x`` and ``y`` are kilometers in the TITAN grid,
not longitude and latitude.

The slider background is the column-maximum reflectivity from the Cartesian
radar files written by Radx2Grid.
"""

import math
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import xarray as xr
from pathlib import Path


OUTLINE_COLOR = "white"

# LROSE display colors for reflectivity, in dBZ. Each color paints the
# interval that starts at the matching edge. The final edge is the top of
# the last interval.
DBZ_EDGES = [
    -20.0, 5.0, 10.0, 20.0, 30.0, 35.0, 36.0, 39.0, 42.0, 45.0,
    48.0, 51.0, 54.0, 57.0, 60.0, 65.0, 70.0, 80.0,
]
DBZ_COLORS = [
    "#404040", "#483d8b", "#005a00", "#007000", "#087fdb", "#1c47e8",
    "#6e0dc6", "#c80f86", "#c06487", "#d2883b", "#fac431", "#fefa03",
    "#fe9a58", "#fe5f05", "#fd341c", "#bebebe", "#d3d3d3",
]

__all__ = [
    "file_list",
    "get_file_date_time",
    "dbz_colorscale",
    "outline_points",
    "plot_complexnum_with_timefile_slider",
]


def file_list(directory_path):
    """Return the file names in ``directory_path``.

    Parameters
    ----------
    directory_path : str
        Directory of Cartesian radar files, for example
        ``./data/radar/cart/20170812``.

    Returns
    -------
    list of str
        File names only, not full paths. The list is empty when the
        directory cannot be read.
    """
    files = []
    try:
        for entry in os.listdir(directory_path):
            full_path = os.path.join(directory_path, entry)
            if os.path.isfile(full_path):
                files.append(entry)
    except FileNotFoundError:
        print("Error: Directory not found at '{}'".format(directory_path))
    except OSError as exc:
        print("An error occurred: {}".format(exc))
    return files


def get_file_date_time(file_name):
    """Return the ``YYYYMMDD_HHMMSS`` stamp from a Radx file name.

    Parameters
    ----------
    file_name : str
        Name such as ``ncf_20170812_161332.nc``. The stamp occupies
        characters 4 through 18.

    Returns
    -------
    str
        For the example above, ``20170812_161332``.
    """
    return file_name[4:19]


def dbz_colorscale():
    """Build the discrete reflectivity colorscale used by the slider.

    Returns
    -------
    ticks : list of int
        Color-bar tick values, in dBZ. The last edge is included.
    colorscale : list of tuple
        Plotly colorscale. Each color is repeated at the start and end of
        its interval so the scale stays discrete.
    """
    edges = DBZ_EDGES
    lower = edges[0]
    span = abs(edges[-1] - lower)
    colorscale = []
    for index in range(len(edges) - 1):
        low = (edges[index] - lower) / span
        high = (edges[index + 1] - lower) / span
        color = DBZ_COLORS[index]
        colorscale.append((low, color))
        colorscale.append((high, color))
    ticks = [int(edge) for edge in edges]
    return ticks, colorscale


def outline_points(xc, yc, rays):
    """Convert clockwise rays from north into TITAN X/Y points.

    Parameters
    ----------
    xc, yc : float
        Storm centroid in kilometers, ``VolCentroidX(km)`` and
        ``VolCentroidY(km)``.
    rays : sequence of float
        Ray lengths in kilometers. Index 0 points north. Index increases
        clockwise by 5 degrees, through a full circle of 72 rays.

    Returns
    -------
    list of tuple
        ``(x, y)`` vertices in kilometers. The first point is not repeated;
        callers close the polygon themselves.
    """
    points = []
    for index, radius in enumerate(rays):
        angle = math.radians(index * 5)
        x = float(xc) + float(radius) * math.sin(angle)
        y = float(yc) + float(radius) * math.cos(angle)
        points.append((x, y))
    return points


def plot_complexnum_with_timefile_slider(z_step, path, df, complexnum, padding_km=18):
    """Plot one complex track as outlines on a reflectivity time slider.

    Parameters
    ----------
    z_step : int
        Accepted so calls can follow the tutorial's other plot functions.
        The background is the column-maximum reflectivity, so this value
        does not select a height.
    path : str
        Directory of Cartesian NetCDF files. File names must look like
        ``ncf_YYYYMMDD_HHMMSS.nc`` and the time stamp must match
        ``date_utc`` in ``df``.
    df : pandas.DataFrame
        Tracks2Ascii table. Required columns are ``ComplexNum``,
        ``SimpleNum``, ``date_utc``, ``VolCentroidX(km)``,
        ``VolCentroidY(km)``, ``MaxDBZ(dBZ)``, and
        ``nPolySidesPolygonRays``.
    complexnum : str or int
        Complex track to draw. ``"17"`` and ``17`` select the same track.
        This is the same selection as
        ``df[df["ComplexNum"] == complexnum]``.
    padding_km : float, optional
        Extra kilometers around the outlines. The axes use one equal span
        in X and Y so a kilometer has the same length in both directions.

    Returns
    -------
    plotly.graph_objects.Figure
        One radar time per slider step. Visible traces are the reflectivity
        image, the filled storm outline, and the simple-track number at
        the centroid.

    Raises
    ------
    ValueError
        If ``complexnum`` is not in ``df``, or if ``path`` has no radar files.
    """
    df0 = df[df["ComplexNum"].astype(str) == str(complexnum)].copy()
    df0 = df0.sort_values("date_utc")
    df0["MaxDBZ(dBZ)"] = pd.to_numeric(df0["MaxDBZ(dBZ)"], errors="coerce")
    df0["date_utc"] = pd.to_datetime(df0["date_utc"], errors="coerce", utc=True)
    if df0.empty:
        raise ValueError("No storms found for ComplexNum = {}".format(complexnum))

    df0["VolCentroidX(km)"] = pd.to_numeric(df0["VolCentroidX(km)"], errors="coerce")
    df0["VolCentroidY(km)"] = pd.to_numeric(df0["VolCentroidY(km)"], errors="coerce")
    df0["time_key"] = df0["date_utc"].dt.strftime("%Y%m%d_%H%M%S")

    outlines_by_time = {}
    all_x = []
    all_y = []
    for _, row in df0.iterrows():
        rays = row["nPolySidesPolygonRays"]
        if not isinstance(rays, (list, tuple)) or len(rays) == 0:
            continue
        xc = float(row["VolCentroidX(km)"])
        yc = float(row["VolCentroidY(km)"])
        points = outline_points(xc, yc, rays)
        record = {
            "simple": str(row["SimpleNum"]),
            "xc": xc,
            "yc": yc,
            "points": points,
        }
        outlines_by_time.setdefault(row["time_key"], []).append(record)
        all_x.extend(x for x, _ in points)
        all_y.extend(y for _, y in points)

    if all_x:
        xmin, xmax = min(all_x) - padding_km, max(all_x) + padding_km
        ymin, ymax = min(all_y) - padding_km, max(all_y) + padding_km
        span = max(xmax - xmin, ymax - ymin)
        xmid, ymid = (xmin + xmax) / 2, (ymin + ymax) / 2
        x_range = [xmid - span / 2, xmid + span / 2]
        y_range = [ymid - span / 2, ymid + span / 2]
    else:
        x_range = [-250, 250]
        y_range = [-250, 250]

    filenames = sorted(file_list(path))
    if not filenames:
        raise ValueError("No radar files found in {}".format(path))
    colorscale_ticks, colorscale_for_go = dbz_colorscale()
    colorscale_labels = [str(tick) for tick in colorscale_ticks]
    fig = go.Figure()
    groups = []

    for file_name in filenames:
        file_key = get_file_date_time(file_name)
        file_path = os.path.join(path, file_name)
        with xr.open_dataset(file_path) as ds:
            x = ds.x0.data
            y = ds.y0.data
            z_max = np.max(ds.DBZ[0], axis=0, keepdims=True)
            z = np.nan_to_num(z_max[0].data, nan=-20)

        idxs = []
        fig.add_trace(go.Heatmap(
            visible=False,
            x=x,
            y=y,
            z=z,
            colorscale=colorscale_for_go,
            colorbar=dict(
                title="dBZ",
                tickvals=colorscale_ticks,
                ticktext=colorscale_labels,
            ),
            name="dBZ",
            zmin=-20,
            zmax=80,
            showscale=True,
        ))
        idxs.append(len(fig.data) - 1)

        for record in outlines_by_time.get(file_key, []):
            closed = record["points"] + [record["points"][0]]
            xs, ys = zip(*closed)
            fig.add_trace(go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                fill="toself",
                fillcolor="rgba(23,105,170,0.16)",
                line=dict(color=OUTLINE_COLOR, width=1.2),
                name="SimpleNum {}".format(record["simple"]),
                visible=False,
                showlegend=False,
                hovertemplate="SimpleNum {}<extra></extra>".format(record["simple"]),
            ))
            idxs.append(len(fig.data) - 1)
            fig.add_trace(go.Scatter(
                x=[record["xc"]],
                y=[record["yc"]],
                mode="markers+text",
                marker=dict(size=5, color=OUTLINE_COLOR),
                text=[record["simple"]],
                textposition="middle center",
                textfont=dict(size=13, color="white"),
                visible=False,
                showlegend=False,
                hoverinfo="skip",
            ))
            idxs.append(len(fig.data) - 1)
            fig.add_trace(go.Scatter(
                x=[record["xc"]],
                y=[record["yc"]],
                mode="text",
                text=[record["simple"]],
                textposition="middle center",
                textfont=dict(size=11, color=OUTLINE_COLOR),
                visible=False,
                showlegend=False,
                hoverinfo="skip",
            ))
            idxs.append(len(fig.data) - 1)
        groups.append(idxs)

    active = 0
    for index, file_name in enumerate(filenames):
        if outlines_by_time.get(get_file_date_time(file_name)):
            active = index
            break
    for index in groups[active]:
        fig.data[index].visible = True

    steps = []
    for index, file_name in enumerate(filenames):
        visible = [False] * len(fig.data)
        for trace_index in groups[index]:
            visible[trace_index] = True
        when = file_name[13:19]
        steps.append(dict(
            method="update",
            args=[
                {"visible": visible},
                {"title": "TITAN storm outlines - ComplexNum = {} - {}".format(complexnum, when)},
            ],
            label=when,
        ))

    fig.update_layout(
        title=steps[active]["args"][1]["title"],
        height=700,
        width=700,
        sliders=[dict(
            active=active,
            currentvalue={"prefix": "time step (HHMMSS): "},
            pad={"t": 50},
            steps=steps,
        )],
        xaxis=dict(title="TITAN X (km)", range=x_range, constrain="domain"),
        yaxis=dict(
            title="TITAN Y (km)",
            range=y_range,
            scaleanchor="x",
            scaleratio=1,
        ),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgb(219,219,219)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgb(219,219,219)", zeroline=False)
    return fig

def read_titan_tracks(path):
    """Read a TITAN Tracks2Ascii file into a DataFrame (one row per storm per scan)."""
    labels = None
    data_lines = []

    with open(path) as f:
        for line in f:
            if line.startswith("#labels:"):
                labels = line[len("#labels:"):].strip().split(",")
            if line.startswith("#") or not line.strip():
                continue
            data_lines.append(line.strip())

    if labels is None:
        raise RuntimeError("No '#labels:' header line found in file")

    # Last label is 'nPolySidesPolygonRays*72': it stands for the ray count + 72 ray values
    fixed_labels = labels[:-1]          # includes 'parents' and 'children'
    n_fixed = len(fixed_labels)         # 78 in your file

    rows, skipped = [], 0
    for line in data_lines:
        parts = line.split()

        # Layout: [n_fixed columns][nPolySides][ray_1 ... ray_n]
        try:
            n_rays = int(parts[n_fixed])
            rays = [float(v) for v in parts[n_fixed + 1:]]
            if len(rays) != n_rays:
                raise ValueError(f"expected {n_rays} rays, found {len(rays)}")
        except Exception as e:
            skipped += 1
            print(f"skipped line ({e}): {line[:80]}...")
            continue

        rows.append(parts[:n_fixed] + [n_rays, rays])

    print(f"parsed: {len(rows)} rows, skipped: {skipped}")

    df = pd.DataFrame(rows, columns=fixed_labels + ["nPolySides", "nPolySidesPolygonRays"])

    # parents/children: keep text like "3,4" or "7,9,11"; "-" means none
    for col in ("parents", "children"):
        df[col] = df[col].replace("-", np.nan)

    # Everything else in the fixed columns is numeric
    numeric_cols = [c for c in fixed_labels if c not in ("parents", "children")]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # Timestamp
    df["date_utc"] = pd.to_datetime(
        dict(
            year=df["Year"].astype(int),
            month=df["Month"].astype(int),
            day=df["Day"].astype(int),
            hour=df["Hour"].astype(int),
            minute=df["Min"].astype(int),
            second=df["Sec"].astype(int),
        ),
        utc=True,
    )
    return df
