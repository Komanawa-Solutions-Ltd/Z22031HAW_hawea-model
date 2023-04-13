"""
Author: matth
Date Created: 22/06/2017 3:53 PM
"""

import tempfile
import time

# required packages:
import numpy as np
import pandas as pd

# builtin packages:
import os
from warnings import warn
from copy import deepcopy
from functools import reduce
from numbers import Number
import sys
from pathlib import Path


# support either version 2 or three python
if sys.version_info.major == 3:
    from itertools import zip_longest
elif sys.version_info.major == 2:
    from itertools import izip_longest as zip_longest

# plotting
from matplotlib.colors import from_levels_and_colors, LogNorm, ListedColormap, SymLogNorm
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.cm import get_cmap

# geospatial
geospatial_loaded = True
try:
    from osgeo import osr, gdal, ogr
    import geopandas as gpd
    import shapely
except ImportError as val:
    warn('could not import one or more geospatial packages,\n'
         '{}\n'
         'this will affect any function that uses geospatial systems'.format(val))
    geospatial_loaded = False


class DummyModelTools_RegularGrid(object):

    def __init__(self, ulx, uly, layers, rows, cols, grid_space,
                 model_version_name, sdp,
                 rotation=0, layer_type=None,
                 no_flow_calc=None, elv_calculator=None,
                 base_map_path=None, default_figsize=(14, 7), epsg_num=2193):
        """
        rotation and differential grid spacing not supported

        :param ulx: upper left x coordinate for the model grid
        :param uly:  the upper left y coordinate for the model grid
        :param layers: the number of layers in the model
        :param rows: the number of rows in the model
        :param cols: the number of columns in the model
        :param grid_space: the grid spacing (must be equally spaced at present)

        :param model_version_name: required the model version name
        :param sdp: the path to the folder containing supporting data (for ease of reference)
        :param rotation: the rotation of the grid
        :param layer_type: the layertypes of the model, e.g. convertable or not

        :param no_flow_calc: the function which is used to return the ibound
        :param elv_calculator: the function whcih is used to return the elevation data base(top,bottoms) shape (k+1,i,j)

        :param base_map_path: the path to a geotiff to allow underlaying it below plots
        :param default_figsize:  the default figure size (in inches) for plots. it can be useful to configure to your
                                 monitor size to minimize the time spent maxing and minning shown figures
        :param epsg_num: the EPSG number to pass to set georeference default is 2193: NZTM
        """

        if rotation != 0:
            raise NotImplementedError('rotations of the model grid have not yet been implemented')

        # used to define the model array and geospatial systems
        self.rotation = rotation
        self.ulx = ulx
        self.uly = uly
        self.grid_space = grid_space
        assert isinstance(layers, int)
        assert isinstance(rows, int)
        assert isinstance(cols, int)
        self.layers = layers
        self.rows = rows
        self.cols = cols

        self.layer_type = layer_type
        self.model_shape = (self.layers, self.rows, self.cols)
        self.model_2d_shape = (self.rows, self.cols)
        self.epsg = epsg_num

        # data managment variables
        self.model_version_name = model_version_name
        self.sdp = sdp
        if self.sdp is not None:
            if not os.path.exists(sdp):
                os.makedirs(sdp)

        # model structure systems
        self._no_flow_calc = no_flow_calc
        self._elv_calculator = elv_calculator

        # plotting support
        self.base_map_path = base_map_path
        self.default_figsize = default_figsize

        # initialise inner classes
        self.modelchecks = self.ModelChecks(self)
        self.plot = self.Plot(self)
        self.io = self.Io(self)

    def get_xlim_ylim(self, return_grouped=True):
        """
        returns the x and y lim of the grid on outside points (e.g. not the cell midpoint)
        :param return_grouped: if True return the data  as (x_min, x_max), (y_min, y_max)
                               else x_min, x_max, y_min, y_max

        :return:(x_min, x_max), (y_min, y_max) or x_min, x_max, y_min, y_max
        """
        x_min, y_min = self.ulx, self.uly - self.grid_space * self.rows
        x_max = x_min + self.grid_space * self.cols
        y_max = self.uly
        if return_grouped:
            return (x_min, x_max), (y_min, y_max)
        else:
            return x_min, x_max, y_min, y_max

    def get_model_x_y(self, grid=True, cell_centers=True):
        """
        returns the x and y coordinates

        :param grid: if True return the grid, else return the 1d arrays
        :param cell_centers: if True return the center of each cell if False return the edges include outside edge
        :return:
        """

        (x_min, x_max), (y_min, y_max) = self.get_xlim_ylim()

        offset = self.grid_space / 2

        if cell_centers:
            # mid points of the array
            x = np.linspace(x_min + offset, x_max - offset, self.cols)
            y = np.flip(np.linspace(y_min + offset, y_max - offset, self.rows))
        else:
            x = np.linspace(x_min, x_max, self.cols + 1)
            y = np.flip(np.linspace(y_min, y_max, self.rows + 1))

        if not grid:
            return x, y
        model_xs, model_ys = np.meshgrid(x, y)
        return model_xs, model_ys

    def get_model_index_grid(self, _3d=False):
        """
        returns grids of self.model_array_shape for each layers, rows, cols to be used for checking things and for
        examining model structure etc.

        :return: layers, rows, cols
        """

        layers = np.arange(self.layers)
        rows = np.arange(self.rows)
        cols = np.arange(self.cols)

        if _3d:
            layers, rows, cols = np.meshgrid(layers, rows, cols, indexing='ij')
            return layers, rows, cols
        else:
            rows, cols = np.meshgrid(rows, cols, indexing='ij')
            return rows, cols

    def get_model_zeros(self, _3d=False):
        """
        returns a numpy zeros array of the model grid

        :param _3d: Boolean if True return a grid of (k,i,j) else (i,j)
        :return:
        """
        if _3d:
            return np.zeros((self.layers, self.rows, self.cols))
        else:
            return np.zeros((self.rows, self.cols))

    def model_where(self, condition):
        """
        quick function to return list of model indexes from a np.where style condition assumes that the array in the
        condition has the shape (k,i,j,) or (i,j)

        :param condition:
        :return: return tuples of i,j or kij
        """
        idx = np.where(condition)
        idx2 = [i for i in zip(*idx)]
        return idx2

    def convert_matrix_to_coords(self, rows, cols, layers=None, i0=None, j0=None,
                                 k0=None, return_z_as_depth=False):
        """
        convert from matix indexing to real world coordinates at the cell center or offset by i0,j0,k0

        :param rows: numeric or array
        :param cols: numeric or array
        :param layers: None or numeric or array
        :param i0: partial portion of the row from 0 to 1 from high row to low row
        :param j0: partial portion of the col from 0 to 1 from low col to high col
        :param k0: partial portion of the layer from 0 to 1 from bottom to top
        :param return_z_as_depth: boolean if True return z as depth from top
        :return: lon, lat if layer is not specified or lon, lat, elv
        """
        if isinstance(rows, Number):
            numeric_data = True
        else:
            numeric_data = False

        if i0 is not None:
            cell_center = False
        else:
            cell_center = True

        if layers is not None:
            three_d = True
        else:
            three_d = False

        rows = np.atleast_1d(rows).astype(int)
        cols = np.atleast_1d(cols).astype(int)

        if rows.shape != cols.shape:
            raise ValueError('rows and cols need be same length')

        if three_d:
            layers = np.atleast_1d(layers).astype(int)
            if rows.shape != layers.shape:
                raise ValueError('rows, cols, layers must be the same length')

        if not cell_center:
            i0 = np.atleast_1d(i0)
            j0 = np.atleast_1d(j0)

            if j0.shape != i0.shape:
                raise ValueError('rows,cols,i0,j0 must be the same length')

            if three_d:
                k0 = np.atleast_1d(k0)
                if k0.shape != j0.shape:
                    raise ValueError('k0 and layers must be the same length')

        model_xs, model_ys = self.get_model_x_y(cell_centers=cell_center)

        lons = model_xs[rows, cols]
        lats = model_ys[rows, cols]
        if not cell_center:
            lats = model_ys[
                rows + 1, cols]  # select the lower lattitude and then add the difference (as io increases with decreasing row value but increasing lat value)
            lons += j0 * self.grid_space
            lats += i0 * self.grid_space

        if layers is None:

            if numeric_data:
                return lons[0], lats[0]
            else:
                return lons, lats

        elv_db = self.get_elv_db()
        thickness = elv_db[0:-1] - elv_db[1:]
        tops = elv_db[0:-1]
        bots = elv_db[1:]
        if cell_center:
            elvs = (tops[layers, rows, cols] + bots[layers, rows, cols]) / 2
        else:
            elvs = bots[layers, rows, cols] + k0 * thickness[layers, rows, cols]

        if return_z_as_depth:
            elvs = tops[np.zeros(layers.shape).astype(int), rows, cols] - elvs

        if numeric_data:
            return lons[0], lats[0], elvs[0]
        else:
            return lons, lats, elvs

    def convert_coords_to_matix(self, lons, lats, elvs=None, return_AE=False,
                                above_top='warn', coords_out_domain='raise'):
        """
        convert from real world coordinates to model indexes by comparing value to center point of array.  Where the value
        is on an edge defaults to top left corner (e.g. row 0, col 0, layer 0)
        partials are defined as:
            i0: partial portion of the row from 0 to 1 from high row to low row
            j0: partial portion of the col from 0 to 1 from low col to high col
            k0: partial portion of the layer from 0 to 1 from bottom to top

        :param lons: longitude in coordinate scheme (number or iterable)
        :param lats: latitude in coordinate scheme(number or iterable)
        :param elvs: elevation in coordinate shceme(number or iterable) or None if None only does the 2d conversion
        :param return_AE: if true return (layer,z0), (row, y0), (col, x0) where x0 ect are the preportion along the cell
                          for use with modpath particles
        :param above_top: 'raise', 'warn', 'pass' to the afformentioned action (set to top of top layer if warn or pass)
                           if a point is above the top of the model
        :param coords_out_domain: 'raise', raise an exception for any coordinates outside of the model domain in any of the three directions
                                  'coerce' return as -1 for all three values
        :return: (row, col) if elvs is not presented or (layer, row, col) or
                  if return_AE (rows, y0), (cols, x0) or (layers, z0s), (rows, y0), (cols, x0)
                  returns are either numbers or numpy array
        """

        if coords_out_domain != 'raise' and coords_out_domain != 'coerce':
            raise ValueError(
                'unexpected value for coords_out_domain {} expected "raise" or "coerce"'.format(coords_out_domain))

        if all((isinstance(lons, Number), isinstance(lats, Number))) and (isinstance(elvs, Number) or elvs is None):
            numeric_data = True
        elif len(lons) == len(lats):
            if elvs is None:
                numeric_data = False
            elif len(lons) == len(elvs):
                numeric_data = False
            else:
                raise ValueError("lats, lons, and elvs must be the same (or elvs can be None)")
        else:
            raise ValueError("lats, lons, and elvs must be the same (or elvs can be None)")

        if numeric_data:
            lons = np.array([lons])
            lats = np.array([lats])
        else:
            lons = np.array(lons)
            lats = np.array(lats)

        (xmin, xmax), (ymin, ymax) = self.get_xlim_ylim()
        cols = ((lons - xmin) / self.grid_space).astype(int)
        rows = ((ymax - lats) / self.grid_space).astype(int)

        idx = (cols < 0) | (cols >= self.cols) | (rows < 0) | (rows >= self.rows)
        if idx.any():
            if coords_out_domain == 'raise':
                raise AssertionError('coords index {} not in model domain'.format(np.where(idx)))
            elif coords_out_domain == 'coerce':
                warn('there are coordinates out of model domain, these will be set to -1')
            else:
                raise ValueError('should not get here')
        x0 = (lons - (cols * self.grid_space + xmin)) / self.grid_space
        y0 = 1 - ((ymax - rows * self.grid_space - lats)) / self.grid_space

        if coords_out_domain == 'coerce':
            cols[idx] = -1
            rows[idx] = -1
            x0[idx] = -1
            y0[idx] = -1

        if elvs is None:
            if return_AE:
                if numeric_data:
                    return (rows[0], y0[0]), (cols[0], x0[0])
                return (rows, y0), (cols, x0)
            else:
                if numeric_data:
                    return rows[0], cols[0]
                return rows, cols

        # convert elvs to layer
        if numeric_data:
            elvs = np.array([elvs])
        else:
            elvs = np.array(elvs)
        elv_db = self.get_elv_db()
        layers = []
        z0s = []
        for i, (id, elv) in enumerate(zip(idx, elvs)):
            if id:
                layer = -1
                z0 = -1
                z0s.append(z0)
                layers.append(layer)
            else:
                top = elv_db[:-1, rows[i], cols[i]]
                bottom = elv_db[1:, rows[i], cols[i]]
                if elv > top.max():
                    if above_top == 'warn':
                        warn('{} value is above top of database setting layer to zero'.format(i))
                        layer = 0
                        z0 = 1
                    elif above_top == 'pass':
                        layer = 0
                        z0 = 1
                    elif above_top == 'raise':
                        raise ValueError('{} value is above top of database'.format(i))
                    else:
                        raise ValueError('unexpected value {} for above_top'.format(above_top))
                else:
                    layer = np.where((top > elv) & (bottom <= elv))
                    if len(layer[0]) > 1:
                        raise ValueError(
                            '{} returns multiple indexes for layer'.format(i))
                    elif len(layer[0]) == 0:
                        if coords_out_domain == 'raise':
                            raise AssertionError('elevation: {} idx {}outside of bounds'.format(elv, i))
                        elif coords_out_domain == 'coerce':
                            layer = -1
                            z0 = -1
                            rows[i] = -1
                            cols[i] = -1
                            y0[i] = -1
                            x0[i] = -1
                    else:
                        layer = layer[0][0]
                        z0 = 1 - (top[layer] - elv) / (top[layer] - bottom[layer])

                layers.append(layer)
                z0s.append(z0)

        layers = np.array(layers)
        z0s = np.array(z0s)
        if return_AE:
            if numeric_data:
                return (layers[0], z0[0]), (rows[0], y0[0]), (cols[0], x0[0])
            return (layers, z0s), (rows, y0), (cols, x0)
        else:
            if numeric_data:
                return layers[0], rows[0], cols[0]
            return layers, rows, cols

    def matrix_out_bounds(self, i, j, k=None):
        """
        are the matrix values out of bounds
        :param i: rows
        :param j: cols
        :param k: None or layers
        :return: bool array (True=out of domain)
        """

        idx = ~np.in1d(i, range(self.rows))
        jdx = ~np.in1d(j, range(self.cols))
        out = jdx | idx
        if k is not None:
            kdx = ~np.in1d(k, range(self.layers))
            out = out | kdx
        return out

    def coord_out_bounds(self, x, y, z=None):
        """
        are the corrdinate values out of bounds
        :param x:
        :param y:
        :param z: None or elevation
        :return: bool array (True=out of domain)
        """
        x = np.atleast_1d(x)
        y = np.atleast_1d(y)
        (x_min, x_max), (y_min, y_max) = self.get_xlim_ylim()
        xidx = (x < x_min) | (x > x_max)
        yidx = (y < y_min) | (y > y_max)
        out = xidx | yidx
        if z is not None:
            tops = self.get_tops()[0]
            bots = self.get_bottoms()[-1]
            row, col = self.convert_coords_to_matix(x[~out], y[~out])
            zidx = (z[out] < bots[row, col]) | (z[out] > tops[row, col])
            out[~out] = out[~out] | zidx

        return out

    def get_elv_db(self, layer=None):
        """
        calculates the elevation database (bottoms with the top of layer one on top or loads pickel
        :param layer: int or None if None return the full database, otherwise return layer of database
        :return: elv_db
        """
        t = time.time()
        elv_db = self._elv_calculator()
        if time.time() - t > 0.5:
            warn('calculating the elvation database took more than 0.5 s, '
                 'it is suggested that your elv calculator function access a saved copy')

        if layer is None:
            return elv_db
        else:
            return elv_db[layer]

    def get_tops(self):
        """
        get the tops of each cell, the max on the layer(k) axis
        :param layer:
        :return:
        """
        return self.get_elv_db()[0:-1]

    def get_bottoms(self):
        """
        get the bottoms of each cell, min on the layer (k) axis
        :return:
        """
        return self.get_elv_db()[1:]

    def get_thickness(self):
        return self.get_tops() - self.get_bottoms()

    def get_fronts(self):
        """
        get the front of each cell the min on the row axis (i) lat assuming NZTM
        where n-s axis is aligned to row1 - rown axis
        :return:
        """
        x, y = self.get_model_x_y(grid=True, cell_centers=True)
        return y - self.grid_space / 2

    def get_backs(self):
        """
        get the back of each cell the min on the row axis (i) y assuming NZTM
        where n-s axis is aligned to row1 - rown axis
        :return:
        """
        x, y = self.get_model_x_y(grid=True, cell_centers=True)
        return y + self.grid_space / 2

    def get_lefts(self):
        """
        get the left side of each cell the min on the column axis (j) x assuming NZTM
        where  E-W axis is aligned to col1 - coln axis
        :return:
        """
        x, y = self.get_model_x_y(grid=True, cell_centers=True)
        return x - self.grid_space / 2

    def get_rights(self):
        """
        get the right side of each cell the max on the column axis (j) x assuming NZTM
        where  E-W axis is aligned to col1 - coln axis
        :return:
        """
        x, y = self.get_model_x_y(grid=True, cell_centers=True)
        return x + self.grid_space / 2

    def get_no_flow(self, layer=None):
        """
        get the ibound values are:
            * v < 0: constant head of the starting heads at the cell.
            * v = 0: in active cell
            * v > 1: active cell

        :param layer: layer to return or None, if None return 3d array
        :return:
        """
        t = time.time()
        no_flow = self._no_flow_calc()
        if time.time() - t > 0.5:
            warn('calculating the no flow layer took more than 0.5 s, '
                 'it is suggested that your no flow calc function access a saved copy')

        if layer is None:
            return no_flow
        else:
            return no_flow[layer]

    @staticmethod
    def np_describe(ndarray, percentiles=(0.01, 0.05, 0.10, 0.25, 0.5, 0.75, 0.90, 0.95, 0.99)):
        """
        pull out the percentiles and put it in a pd.Series

        :param ndarray: a 1 or more dimentional numpy array
        :param percentiles: percentiles to return
        :return: pd.Series
        """
        outdata = pd.Series()
        outdata.loc['mean'] = np.nanmean(ndarray)
        outdata.loc['std'] = np.nanstd(ndarray)
        outdata.loc['min'] = np.nanmin(ndarray)
        for i in percentiles:
            outdata.loc['{}%'.format(int(i * 100))] = np.nanpercentile(ndarray, i * 100)
        outdata.loc['max'] = np.nanmax(ndarray)
        return outdata

    @staticmethod
    def grouper(n, iterable, fillvalue=None):
        """
        group up the iterable into groups of size n, fill excess with the fill value
        grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx

        :param n: number of components per group
        :param iterable: the iterable to group
        :param fillvalue: the value to fill
        :return:
        """

        args = [iter(iterable)] * n
        return zip_longest(fillvalue=fillvalue, *args)

    @staticmethod
    def circ_mean_np(angles):
        """
        circular mean (e.g. circ_mean([10,350]) = 0
        :param angles: angles to mean, in degrees
        :return:
        """
        rads = np.deg2rad(angles)
        av_sin = np.mean(np.sin(rads))
        av_cos = np.mean(np.cos(rads))
        ang_rad = np.arctan2(av_sin, av_cos)
        ang_deg = np.rad2deg(ang_rad)
        ang_deg = np.mod(ang_deg, 360.)
        return ang_deg

    class ModelChecks(object):
        def __init__(self, parent):
            """
            a inner class to handle all of the plotting systems

            :param parent: to access the ModelTools instance
            """
            self._parent = parent

        @staticmethod
        def modflow_converged(list_path=None, lines=None, false_on_missing=True):
            """
            returned convergence of the model

            :param list_path: path to the list file (str/Path object) or file object with .readlines()
            :return: True if converged, False if not, None if not realised
            """
            # could make this faster by only loading the last n lines? or through a regular expression?,
            # but not super slow
            if not os.path.exists(list_path):
                if false_on_missing:
                    return False
                else:
                    raise FileNotFoundError(f'could not find list file: {list_path}')
            converg = True
            end_negs = ['FAILED TO MEET SOLVER'.lower(),
                        'FAILURE TO MEET SOLVER'.lower()]
            assert not (list_path is None and lines is None)
            if list_path is not None:
                assert lines is None
                if isinstance(list_path, str) or isinstance(list_path, Path):
                    with open(list_path, 'r') as f:
                        lines = f.readlines()
                        # decode lines if bytes object
                        lines = [e.decode() if isinstance(e, bytes) else e for e in lines]
                else:
                    try:
                        lines = list_path.readlines()
                        # decode lines if bytes object
                        lines = [e.decode() if isinstance(e, bytes) else e for e in lines]
                    except AttributeError as val:
                        raise ValueError(f'expected list_path to be a str, Path, or file object; got: {type(list_path)}'
                                         f'raised: {val}')
            lines = pd.Series(lines)
            lines = lines.str.lower()
            failure_noted = [lines.str.contains(e).any() for e in end_negs]
            if any(failure_noted):
                return False
            return True

        @staticmethod
        def modpath_converged(mplist_path):
            """
            check if the modpath simulation converged

            :param mplist_path: path to the modpath list file
            :return: Bool converged
            """
            # could make this faster by only loading the last n lines? or through a regular expression?,
            # but not super slow
            with open(mplist_path) as f:
                out = 'Normal termination' in f.read()
            return out

        @staticmethod
        def mt3d_converged(list_path):
            """
            check if the MT3D simulation converged

            :param list_path: path to the MT3D list file
            :return: Bool converged
            """
            # could make this faster by only loading the last n lines? or through a regular expression?, but not super slow
            with open(list_path) as f:
                lines = f.readlines()
            converged = ' | 3 D | END OF MODEL OUTPUT\n' in lines
            return converged

    class Plot(object):

        def __init__(self, parent):
            """
            a inner class to handle all of the plotting systems

            :param parent: to access the ModelTools instance
            """
            self._parent = parent

        @staticmethod
        def get_colors(vals, cmap='tab10'):
            n_scens = len(vals)
            if n_scens < 20:
                cmap = get_cmap(cmap)
                colors = [cmap(e / (n_scens + 1)) for e in range(n_scens)]
            else:
                colors = []
                i = 0
                cmap = get_cmap(cmap)
                for v in vals:
                    colors.append(cmap(i / 20))
                    i += 1
                    if i == 20:
                        i = 0
            return colors

        @staticmethod
        def show():
            """
            a short cut to be able to show plots without importing matplotlib.pyplot

            :return:
            """
            plt.show()

        @staticmethod
        def close(fig=None):
            """
            a shortcut to be able to close plots without importing matplotlib.pyplot

            :param fig: see matplotlib.pyplot.close()
            :return:
            """
            plt.close(fig)

        def plt_matrix(self, array, vmin=None, vmax=None, title=None, no_flow_layer=None, ax=None, color_bar=True,
                       base_map=False, plt_background=True, background_alpha=0.5, cbar_lab=None,
                       cbarlabelpad=15, contour=False, norm=None,
                       contour_levels=None, cmap='plasma',
                       label_contours=False, contour_label_format='%1.1f', color_mesh=True, constrained_layout=False,
                       **kwargs):
            """
            plot a 2d model array

            :param array: they array to plot (of i,j)
            :param vmin: vmin to pass to the plot
            :param vmax: vmax to pass to the plot
            :param title: a title to include on the plot
            :param no_flow_layer: the layer to plot the no flow boundry on
            :param ax: None or a matplotlib ax to plot on top of, not frequently used (execpt in subplots)
            :param color_bar: Boolean if true plot a color bar scale
            :param base_map: Boolean if True underlie the plot with greyscale basemap of the region the map is defined by
                             self.base_map_pathsets default alpha to 0.5
            :param log: boolean if true plot the log of the data
            :param plt_background: Boolean if True plot the noflow boundary as black
            :param background_alpha: alpha to apply to background
            :param cbar_lab: string to lable the cbar
            :param contour: boolean if true print black contours on the map
            :param contour_levels: see levels in matplotlib.pyplot.contour, or float/int, If float/int then
                                   contour levels are calculated from array.min()//level*level to array.max()//level
                                   *level
            :param cmap: color map to use
            :param label_contours: boolean if true then print labels in line with the contours
            :param contour_label_format: format for the contour label (see fmt in plt.clabel)
            :param color_mesh: bool if True will plot the color mesh else, will not
            :param kwargs: other kwargs passed to matplotlib.pcolor alpha is the only kwarg that is also passed to the background
            :return: fig, ax
            """
            # why are there two axes???? because the colorbar is treated as a second ax
            alpha = 1
            assert array.shape == self._parent.model_2d_shape, (f'expected model shape: {self._parent.model_2d_shape} '
                                                                f'got: {array.shape}')
            array = deepcopy(array.astype(float))
            if no_flow_layer is not None:
                no_flow = self._parent.get_no_flow(no_flow_layer)
                array[no_flow < 1] = np.nan

            if vmax is None:
                vmax = np.nanmax(array)
            if vmin is None:
                vmin = np.nanmin(array)

            if base_map:
                if ax is not None:
                    warn('setting basemap will overwrite the data already in the axes')
                if 'alpha' not in kwargs:
                    alpha = 0.5
            fig, ax = self.plt_basemap(ax=ax, no_flow_layer=no_flow_layer, plt_background=plt_background,
                                       background_alpha=background_alpha, base_map=base_map)
            model_xs_edge, model_ys_edge = self._parent.get_model_x_y(cell_centers=False)
            model_xs, model_ys = self._parent.get_model_x_y(cell_centers=True)

            if 'alpha' in kwargs:
                alpha = kwargs['alpha']
                kwargs.pop('alpha')

            if alpha == 1:
                linewidth = None
                edgecolors = 'face'
            else:
                edgecolors = 'face'
                linewidth = 0

            if norm is not None:
                if norm == 'log':
                    if vmin < 0 or vmax < 0:
                        raise ValueError('cannot use norm = log if vmin or vmax <0, try passing a SymLogNorm')
                    norm = LogNorm(vmin=vmin, vmax=vmax)

                vmax = None
                vmin = None

            if color_mesh:
                pcm = ax.pcolormesh(model_xs_edge, model_ys_edge, np.ma.masked_invalid(array),
                                    cmap=cmap, vmin=vmin, vmax=vmax, alpha=alpha, edgecolors=edgecolors,
                                    linewidth=linewidth, norm=norm, antialiased=True, **kwargs)
                if color_bar:
                    cbar = fig.colorbar(pcm, ax=ax, extend='max')
                    cbar.set_alpha(1)
                    cbar.draw_all()
                    if cbar_lab is not None:
                        cbar.ax.set_ylabel(cbar_lab, rotation=270,
                                           labelpad=cbarlabelpad)

            if contour:
                if contour_levels is not None and not hasattr(contour_levels, '__len__'):
                    # contour levels is step size
                    contour_levels = np.arange(np.nanmin(array) // contour_levels * contour_levels,
                                               np.nanmax(array) // contour_levels * contour_levels,
                                               contour_levels)

                cs = ax.contour(model_xs, model_ys, array, levels=contour_levels,
                                colors='k')
                if label_contours:
                    ax.clabel(cs, inline=1, fontsize=10, fmt=contour_label_format)

            if title is not None:
                ax.set_title(title)
            fig.set_constrained_layout(constrained_layout)
            return fig, ax

        def plt_discrete_matrix(self, array, colors=None, cmap=None, names=None, legend_loc=None,
                                color_bar=False, return_handles_labels=False, **kwargs):
            """
            plot discrete arrays
            :param array: array with integer values (to float) (or nan values, which are not plotted)
            :param colors: {int(value): color}
            :param cmap: colormap to pass to self.get_colors
            :param names: dict {int(value): name}
            :param legend_loc: location to plot legend ax.legend(loc=legend_loc)
            :param color_bar: bool plot colorbar, default is false
            :param kwargs: kwargs to pass to self.plt_matrix
            :return:
            """
            assert isinstance(names, dict) or names is None
            assert isinstance(colors, dict) or colors is None

            assert isinstance(array, np.ndarray)
            assert array.shape == self._parent.model_2d_shape
            temp_values = [int(e) for e in np.unique(array.flatten()) if np.isfinite(e)]
            if names is None:
                values = temp_values
                names = {e: str(e) for e in temp_values}
            else:
                values = names.keys()
            assert set(values).issuperset(set(temp_values)), (f'expected values: {temp_values} and '
                                                              f'passed values: {values} do not match')
            values = sorted(set(values).intersection(temp_values))

            use_array = np.zeros(array.shape) * np.nan
            for i, v in enumerate(values):
                use_array[np.isclose(array, v)] = i
            if cmap is not None and colors is not None:
                raise ValueError('cmap cannot be specified if colors are not None')
            if colors is None:
                assert cmap is not None, 'if colors are not specified then cmap must be specified'
                colors = {v: c for c, v in zip(self.get_colors(values, cmap=cmap), values)}

            usecmap = ListedColormap([colors[v] for v in values])
            fig, ax = self.plt_matrix(use_array, cmap=usecmap, color_bar=color_bar, **kwargs)
            handles, labels = [], []
            for v in values:
                handles.append(Patch(facecolor=colors[v]))
                labels.append(names[v])
            ax.legend(handles, labels, loc=legend_loc)
            if return_handles_labels:
                return fig, ax, handles, labels
            else:
                return fig, ax

        def plt_basemap(self, ax=None, no_flow_layer=None, plt_background=True, background_alpha=0.5,
                        base_map=True):
            """
            plots the basemap on the given axis

            :param ax: matplotlib.ax or None, if None then a fig and ax is created
            :param no_flow_layer: the layer to plot the no flow boundry on
            :param plt_background: Boolean if True plot the noflow boundary as black
            :param background_alpha: alpha to apply to background
            :param base_map: bool if true plot smt.base_map_path
            :return:
            """
            if ax is None:
                fig, ax = plt.subplots(figsize=self._parent.default_figsize)
            else:
                fig = ax.figure
            if base_map:
                assert geospatial_loaded, 'the geospatial packages are required to plot basemaps'
                if self._parent.base_map_path is None:
                    raise ValueError('in order to use base_map self.base_map_path must be defined')
                ds = gdal.Open(str(self._parent.base_map_path))
                width = ds.RasterXSize
                height = ds.RasterYSize
                gt = ds.GetGeoTransform()
                minx = gt[0]
                miny = gt[3] + width * gt[4] + height * gt[5]
                maxx = gt[0] + width * gt[1] + height * gt[2]
                maxy = gt[3]

                image = ds.ReadAsArray()
                if image.ndim == 3:  # if a rgb image then plot as greyscale
                    image = image.mean(axis=0)
                ll = (minx, miny)
                ur = (maxx, maxy)

                ax.imshow(image, extent=[ll[0], ur[0], ll[1], ur[1]], cmap='gray')  #
            xlim, ylim = self._parent.get_xlim_ylim()
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            ax.set_aspect('equal')

            if no_flow_layer is not None and plt_background:
                if background_alpha == 1:
                    bk_linewidth = None
                    bk_edgecolors = 'face'
                else:
                    bk_edgecolors = 'face'
                    bk_linewidth = 0
                model_xs_edge, model_ys_edge = self._parent.get_model_x_y(cell_centers=False)
                no_flow = self._parent.get_no_flow(no_flow_layer).astype(float)
                no_flow[no_flow == 1] = np.nan
                cmap, norm = from_levels_and_colors([-100, 0], ['cyan', 'black', 'black'], extend='both')
                ax.pcolormesh(model_xs_edge, model_ys_edge, np.ma.masked_invalid(no_flow), cmap=cmap,
                              alpha=background_alpha, edgecolors=bk_edgecolors, linewidth=bk_linewidth,
                              antialiased=True)

            return fig, ax

        @staticmethod
        def set_plot_lims_padded(x_coords, y_coords, padding, ax):
            """
            limt a plots extent by x/ycoods and a padding (in map units)
            :param x_coords: 1 or more coordiantes
            :param y_coords: 1 or more coordiantes
            :param padding: padding in map units on each side
            :param ax: axes to limit
            :return:
            """
            x_coords = np.atleast_1d(x_coords)
            y_coords = np.atleast_1d(y_coords)
            xbound = x_coords.max() - x_coords.min()
            ybound = y_coords.max() - y_coords.min()
            use_pad = max(xbound, ybound)
            use_xpad = (use_pad - xbound) / 2
            use_ypad = (use_pad - ybound) / 2
            ax.set_xlim(x_coords.min() - padding - use_xpad,
                        x_coords.min() + use_xpad + xbound + padding)
            ax.set_ylim(y_coords.min() - padding - use_ypad,
                        y_coords.min() + use_ypad + ybound + padding)

    class Io(object):
        def __init__(self, parent):
            """
            subclass to handle all of the IO systems and some export data management

            :param parent: parent class to give access to partent attributes
            """
            self._parent = parent

        def add_mxmy_to_df(self, df, add_elv=False, add_depth=False):
            """
            adds the x and y centroid of the cells to a dataframe with either row,col or i,j in the keys

            :param df: pandas.DataFrame
            :param add_elv:  boolean if True then add teh elevation of the cell center to the database
            :param add_depth: boolean if True then add the depth from surface of the cell center to the database
            :return:
            """
            df = deepcopy(df)
            if 'mx' in df.keys() or 'my' in df.keys():
                warn('mx or my present in dataframe, this will be overwritten')

            try:
                rows = df.loc[:, 'row']
                cols = df.loc[:, 'col']
            except KeyError:
                rows = df.loc[:, 'i']
                cols = df.loc[:, 'j']

            x, y = self._parent.convert_matrix_to_coords(rows, cols)
            df.loc[:, 'mx'] = x
            df.loc[:, 'my'] = y

            if add_elv or add_depth:
                try:
                    layers = df.loc[:, 'layer']
                except KeyError:
                    layers = df.loc[:, 'k']

            if add_depth:
                lat, lon, df.loc[:, 'mdepth'] = self._parent.convert_matrix_to_coords(rows, cols, layers,
                                                                                      return_z_as_depth=True)

            if add_elv:
                lat, lon, df.loc[:, 'mz'] = self._parent.convert_matrix_to_coords(rows, cols, layers,
                                                                                  return_z_as_depth=False)

            return df

        def array_to_raster(self, path, array, no_flow_layer=None):
            """
            saves a 2d model array as a raster geotiff file

            :param path: path to save the raster
            :param array: array to save (must be 2d model array)
            :param no_flow_layer: None or int the no-flow layer to mask the array on
            :return:
            """
            # keynote for some reason this is not being recognised as having the correct CRS
            assert geospatial_loaded, 'the geospatial packages are required for array_to_raster'
            path = str(path)
            null_val = -999999

            if array.shape != (self._parent.model_2d_shape):
                raise ValueError('array must match model 2d grid shape')
            if no_flow_layer is not None:
                no_flow = self._parent.get_no_flow(no_flow_layer).astype(bool)
                array[~no_flow] = null_val
            output_raster = gdal.GetDriverByName('GTiff').Create(path, array.shape[1], array.shape[0], 1,
                                                                 gdal.GDT_Float32)  # Open the file
            geotransform = (self._parent.ulx, self._parent.grid_space, 0, self._parent.uly, 0, -self._parent.grid_space)
            output_raster.SetGeoTransform(geotransform)  # Specify its coordinates
            srs = osr.SpatialReference()  # Establish its coordinate encoding
            srs.ImportFromEPSG(self._parent.epsg)  # set the georefernce
            output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system
            # to the file
            band = output_raster.GetRasterBand(1)
            band.WriteArray(array)  # Writes my array to the raster
            band.FlushCache()
            band.SetNoDataValue(null_val)

        def geodb_to_model_array(self, path, shape_name, attribute, alltouched=False,
                                 area_statistics=False, fine_spacing=10, resample_method='average'
                                 ):
            """
            create model array from a shapefile in a geodatabase

            :param path: path to geodatabase
            :param shape_name: name of the shape file
            :param attribute: name of the attribute to convert to matrix
            :param area_statistics: boolean if true first burn the raster at a finer detail and do some statistics to
                                    group up
            :param fine_spacing: int m of spacing to burn the raster to (limits the polygon overlay),
                                 only used if area_statistics is True
            :param resample_method: key to define resampling options
                                    near:
                                        nearest neighbour resampling (default, fastest algorithm, worst interpolation
                                        quality).
                                    bilinear:
                                        bilinear resampling.
                                    cubic:
                                        cubic resampling.
                                    cubicspline:
                                        cubic spline resampling.
                                    lanczos:
                                        Lanczos windowed sinc resampling.
                                    average:
                                        average resampling, computes the average of all non-NODATA contributing pixels.
                                         (GDAL >= 1.10.0)
                                    mode:
                                        mode resampling, selects the value which appears most often of all the
                                        sampled points. (GDAL >= 1.10.0)
                                    max:
                                        maximum resampling, selects the maximum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    min:
                                        minimum resampling, selects the minimum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    med:
                                        median resampling, selects the median value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q1:
                                        first quartile resampling, selects the first quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q3:
                                        third quartile resampling, selects the third quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)

            :return: np array of the matrix
            """
            assert geospatial_loaded, 'the geospatial packages are required for geodb_to_model_array'
            driver = ogr.GetDriverByName("OpenFileGDB")
            ds = driver.Open(path, 0)
            source_layer = ds.GetLayer(shape_name)

            outdata = self._layer_to_model_array(source_layer, attribute, alltouched=alltouched,
                                                 area_statistics=area_statistics, fine_spacing=fine_spacing,
                                                 resample_method=resample_method, path=str(path) + str(shape_name))
            return outdata

        def shape_file_to_model_array(self, path, attribute, alltouched=False,
                                      area_statistics=False, fine_spacing=10, resample_method='average'):
            """
            shape file to vistas array

            :param path: path to shapefile
            :param attribute: attribute name to convert
            :param area_statistics: boolean if true first burn the raster at a finer detail and do some statistics to
                                    group up
            :param fine_spacing: int m of spacing to burn the raster to (limits the polygon overlay),
                                 only used if area_statistics is True
            :param resample_method: key to define resampling options
                                    near:
                                        nearest neighbour resampling (default, fastest algorithm, worst interpolation
                                        quality).
                                    bilinear:
                                        bilinear resampling.
                                    cubic:
                                        cubic resampling.
                                    cubicspline:
                                        cubic spline resampling.
                                    lanczos:
                                        Lanczos windowed sinc resampling.
                                    average:
                                        average resampling, computes the average of all non-NODATA contributing pixels.
                                         (GDAL >= 1.10.0)
                                    mode:
                                        mode resampling, selects the value which appears most often of all the
                                        sampled points. (GDAL >= 1.10.0)
                                    max:
                                        maximum resampling, selects the maximum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    min:
                                        minimum resampling, selects the minimum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    med:
                                        median resampling, selects the median value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q1:
                                        first quartile resampling, selects the first quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q3:
                                        third quartile resampling, selects the third quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)

            :return:  np.array of the data in model format
            """
            # open shape file
            assert geospatial_loaded, 'the geospatial packages are required for shape_file_to_model_array'
            source_ds = ogr.Open(str(path))
            source_layer = source_ds.GetLayer()

            outdata = self._layer_to_model_array(source_layer, attribute, alltouched=alltouched,
                                                 area_statistics=area_statistics, fine_spacing=fine_spacing,
                                                 resample_method=resample_method, path=path)
            return outdata

        def _layer_to_model_array(self, source_layer, attribute, alltouched,
                                  area_statistics, fine_spacing, resample_method, path):
            """
            hidden function to convert a source layer to a rasterized np array

            :param source_layer: from either function above
            :param attribute: attribute to convert.
            :param area_statistics: boolean if true first burn the raster at a finer detail and do some statistics to
                                    group up
            :param fine_spacing: int m of spacing to burn the raster to (limits the polygon overlay),
                                 only used if area_statistics is True.  fine spacing will be adusted to be a whole factor of
                                 self.grid_space
            :param resample_method: key to define resampling options
                                    near:
                                        nearest neighbour resampling (default, fastest algorithm, worst interpolation
                                        quality).
                                    bilinear:
                                        bilinear resampling.
                                    cubic:
                                        cubic resampling.
                                    cubicspline:
                                        cubic spline resampling.
                                    lanczos:
                                        Lanczos windowed sinc resampling.
                                    average:
                                        average resampling, computes the average of all non-NODATA contributing pixels.
                                         (GDAL >= 1.10.0)
                                    mode:
                                        mode resampling, selects the value which appears most often of all the
                                        sampled points. (GDAL >= 1.10.0)
                                    max:
                                        maximum resampling, selects the maximum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    min:
                                        minimum resampling, selects the minimum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    med:
                                        median resampling, selects the median value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q1:
                                        first quartile resampling, selects the first quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q3:
                                        third quartile resampling, selects the third quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
            :return:  np array of rasterized data
            """
            assert geospatial_loaded, 'the geospatial packages are required for layer_to_model_array based functions'

            if area_statistics:
                fs = np.array(list(_factors(self._parent.grid_space)))
                fine_spacing = fs[np.argmin(np.abs(fs - fine_spacing))]
                assert self._parent.grid_space % fine_spacing == 0, 'should not get here: fine spacing {} must be an ' \
                                                                    'even factor of gridspacing: {}'.format(
                    fine_spacing,
                    self._parent.grid_space)
                trans = self._parent.grid_space / fine_spacing
                cols = int(self._parent.cols * trans)
                rows = int(self._parent.rows * trans)
                pixelWidth = pixelHeight = fine_spacing  # depending how fine you want your raster
            else:
                cols = self._parent.cols
                rows = self._parent.rows
                pixelWidth = pixelHeight = self._parent.grid_space  # depending how fine you want your raster

            x_min, y_min = self._parent.ulx, self._parent.uly - self._parent.grid_space * self._parent.rows

            with tempfile.TemporaryDirectory() as temp_dir:
                target_ds = gdal.GetDriverByName('GTiff').Create('{}/temp.tif'.format(temp_dir), cols,
                                                                 rows,
                                                                 1,
                                                                 gdal.GDT_Float64)
                target_ds.SetGeoTransform((x_min, pixelWidth, 0, y_min, 0, pixelHeight))
                band = target_ds.GetRasterBand(1)
                NoData_value = -999999
                band.Fill(NoData_value)
                band.SetNoDataValue(NoData_value)
                band.FlushCache()
                if alltouched:
                    opt = ["ALL_TOUCHED=TRUE", 'a_nodata={}'.format(NoData_value),
                           "ATTRIBUTE={}".format(attribute), 'initValues={}'.format(NoData_value)]
                else:
                    opt = ['a_nodata={}'.format(NoData_value), "ATTRIBUTE={}".format(attribute),
                           'initValues={}'.format(NoData_value)]
                gdal.RasterizeLayer(target_ds, [1], source_layer, options=opt)
                target_dsSRS = osr.SpatialReference()
                target_dsSRS.ImportFromEPSG(self._parent.epsg)
                target_ds.SetProjection(target_dsSRS.ExportToWkt())
                target_ds = None
                temp_file = '{}/temp.tif'.format(temp_dir)
                if area_statistics:
                    if resample_method == 'mean':
                        resample_method = 'average'
                    gdal.Warp('{}/temp2.tif'.format(temp_dir), temp_file,
                              xRes=self._parent.grid_space, yRes=self._parent.grid_space, resampleAlg=resample_method)
                    os.remove(temp_file)
                    temp_file = '{}/temp2.tif'.format(temp_dir)

                f = gdal.Open(temp_file)
                outdata = f.ReadAsArray()
                f = None
            if not area_statistics:
                outdata = np.flipud(outdata)
            outdata[np.isclose(outdata, -999999)] = np.nan
            if 0 in outdata:
                warn(
                    f'0 value in the burned array from {path} this may be an actual value or may be a null value as shapefiles '
                    'store null values as 0 for integer fileds')

            return outdata

        def raster_to_array(self, raster_path, resample_method, raster_band=1):
            """
            map a raster found at raster_path to a model array regardless of different grid_sizes
            :param raster_path:
            :param resample_method: key to define resampling options
                                    near:
                                        nearest neighbour resampling (default, fastest algorithm, worst interpolation
                                        quality).
                                    bilinear:
                                        bilinear resampling.
                                    cubic:
                                        cubic resampling.
                                    cubicspline:
                                        cubic spline resampling.
                                    lanczos:
                                        Lanczos windowed sinc resampling.
                                    'average' or 'mean':
                                        average resampling, computes the average of all non-NODATA contributing pixels.
                                         (GDAL >= 1.10.0)
                                    mode:
                                        mode resampling, selects the value which appears most often of all the
                                        sampled points. (GDAL >= 1.10.0)
                                    max:
                                        maximum resampling, selects the maximum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    min:
                                        minimum resampling, selects the minimum value from all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    med:
                                        median resampling, selects the median value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q1:
                                        first quartile resampling, selects the first quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
                                    q3:
                                        third quartile resampling, selects the third quartile value of all non-NODATA
                                        contributing pixels. (GDAL >= 2.0.0)
            :param raster_band: int, the raster band to read, default assumes band 1

            :return:
            """
            if not os.path.exists(raster_path):
                raise FileNotFoundError(f'{raster_path} not found')
            _rs_methods = ['near', 'bilinear', 'cubic', 'cubicspline', 'lanczos', 'average', 'mode', 'max', 'min',
                           'med', 'q1', 'q3', ]
            if resample_method == 'mean':
                resample_method = 'average'
            assert resample_method in _rs_methods, f'{resample_method} not defined please use one of {_rs_methods}'

            x_min, x_max, y_min, y_max = self._parent.get_xlim_ylim(False)
            with tempfile.TemporaryDirectory() as temp_dir:
                gdal.Warp(os.path.join(temp_dir, 'temp2.tif'), str(raster_path),
                          xRes=self._parent.grid_space, yRes=self._parent.grid_space, resampleAlg=resample_method,
                          outputBounds=(x_min, y_min, x_max, y_max)
                          )
                temp_file = '{}/temp2.tif'.format(temp_dir)
                f = gdal.Open(temp_file)
                f2 = f.GetRasterBand(raster_band)
                no_data = f2.GetNoDataValue()  # needs to be done in two lines for some reason... I think the file was
                # closed by gdal.
                outdata = f2.ReadAsArray()
                f = None

            if no_data is not None:
                outdata = outdata.astype(float)
                outdata[np.isclose(outdata, no_data)] = np.nan

            return outdata


# supporting functions and classes
def _factors(n):
    return set(reduce(list.__add__,
                      ([i, n // i] for i in range(1, int(pow(n, 0.5) + 1)) if n % i == 0)))
