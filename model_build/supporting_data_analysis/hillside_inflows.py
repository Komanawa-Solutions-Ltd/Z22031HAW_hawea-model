"""
created matt_dumont 
on: 2/08/22
"""
import pandas as pd
import numpy as np
from project_base import base_model_data_dir, processed_model_data_dir, modelling_dir, unbacked_dir
from model_build.project_model_tools import smt
import geopandas as gpd
import datetime
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from copy import deepcopy

# exclude lagoon creek races instead manage as additional points of well inflow


pour_points_path = base_model_data_dir.joinpath('hillflow_inputs.shp')
catchment_area_path = processed_model_data_dir.joinpath('catchment_areas.csv')
luggate_catch_area_path = processed_model_data_dir.joinpath('luggate_catchment_area.csv')

catchment_loc_path = processed_model_data_dir.joinpath('catchment_locs.csv')
flow_data_path = processed_model_data_dir.joinpath('hillside_flows.csv')


def get_hillside_catchment_locs(recalc=False):
    if not recalc and catchment_loc_path.exists():
        outdata = pd.read_csv(catchment_loc_path, dtype=int)
        dtypes = {
            'i': 'int64',
            'j': 'int64',
            'px': float,
            'py': float,
            'mx': float,
            'my': float,
        }

        for k, v in dtypes.items():
            outdata.loc[:, k] = outdata.loc[:, k].astype(v)
        return outdata
    catchments = get_catchment_areas()
    ibound = smt.get_no_flow(0)
    outdata = catchments.loc[:, ['px', 'py', 'group']]
    i, j = smt.convert_coords_to_matix(lons=outdata.loc[:, 'px'], lats=outdata.loc[:, 'py'])
    outdata.loc[:, 'i'] = i
    outdata.loc[:, 'j'] = j

    move_direction = {
        'maungawera': ('i', 1),
        'flat_west': ('j', 1),
        'flat_east': ('j', -1),
        'terrace_east': ('j', -1),
        'south_east': ('j', -1),
        'mt_brown': ('j', 1),
    }
    temp = (ibound[outdata.loc[:, 'i'], outdata.loc[:, 'j']]) == 0
    while temp.any():
        if smt.matrix_out_bounds(i=outdata.loc[:, 'i'], j=outdata.loc[:, 'j']).any():
            raise ValueError('went out of bounds')
        for g, (k, v) in move_direction.items():
            idx = temp & (outdata.group == g)
            outdata.loc[idx, k] += v

        temp = (ibound[outdata.loc[:, 'i'], outdata.loc[:, 'j']]) == 0
    outdata = smt.io.add_mxmy_to_df(outdata)
    fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, no_flow_layer=0, base_map=True, title='moved points')
    ax.scatter(outdata.px, outdata.py, c='r', label='first')
    ax.scatter(outdata.mx, outdata.my, c='b', label='new')
    for mx, px, my, py in outdata.loc[:, ['mx', 'px', 'my', 'py']].itertuples(False, None):
        ax.plot([mx, px], [my, py], c='k')
    smt.plot.show()

    outdata.reset_index()
    outdata = outdata.drop(index='ss22')
    outdata.to_csv(catchment_loc_path)
    return outdata


def get_catchment_areas(show_plot=False, recalc=False):
    if catchment_area_path.exists() and not recalc:
        data = pd.read_csv(catchment_area_path, index_col=0)
        return data

    dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')
    catchment_shapefile_dir = unbacked_dir.joinpath('input_data/hillside_catchments')
    catchment_shapefile_dir.mkdir(exist_ok=True, parents=True)

    from pysheds.grid import Grid
    grid = Grid.from_raster(str(dem_path))
    dem = grid.read_raster(str(dem_path))
    # Fill pits in DEM
    pit_filled_dem = grid.fill_pits(dem)

    # Fill depressions in DEM
    flooded_dem = grid.fill_depressions(pit_filled_dem)

    # Resolve flats in DEM
    inflated_dem = grid.resolve_flats(flooded_dem)
    print('dem conditioned')

    # Compute flow directions (d8)
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    fdir = grid.flowdir(inflated_dem, dirmap=dirmap)

    # Calculate flow accumulation
    acc = grid.accumulation(fdir, dirmap=dirmap)
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_alpha(0)
    plt.grid('on', zorder=0)
    im = ax.imshow(acc, extent=grid.extent, zorder=2,
                   cmap='cubehelix',
                   norm=LogNorm(1, acc.max()),
                   interpolation='bilinear')

    plt.colorbar(im, ax=ax, label='Upstream Cells')
    plt.title('Flow Accumulation', size=14)
    plt.xlabel('NZTMX')
    plt.ylabel('NZTMY')
    plt.tight_layout()
    if show_plot:
        plt.show()

    pourpoints = gpd.read_file(pour_points_path)
    outdata = pd.DataFrame(index=pourpoints.River_name, columns=['raster_area', 'shp_area', 'px', 'py'])
    for i, pp in pourpoints.iterrows():
        # Delineate a catchment
        # ---------------------
        # Specify pour point
        x = pp.geometry.x
        y = pp.geometry.y
        name = pp.River_name
        group = pp.group
        print(name)
        outdata.loc[name, 'px'] = x
        outdata.loc[name, 'py'] = y
        outdata.loc[name, 'group'] = group

        # Snap pour point to high accumulation cell
        x_snap, y_snap = grid.snap_to_mask(acc > 1000, (x, y))

        # Delineate the catchment
        catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap,
                               xytype='coordinate')
        # calculate area
        cell_area = 15 * 15  # m2 from 15m dem
        catch_area = catch.sum() * cell_area
        outdata.loc[name, 'raster_area'] = catch_area

        # export shapefile to check
        grid2 = deepcopy(grid)
        grid2.clip_to(catch)
        catch_view = grid2.view(catch)
        _write_shapefile(outpath=catchment_shapefile_dir.joinpath(f'{name}.shp'), grid=grid2, catch_view=catch_view)
        t = gpd.read_file(catchment_shapefile_dir.joinpath(f'{name}.shp'))
        outdata.loc[name, 'shp_area'] = t.area.sum()

    outdata.to_csv(catchment_area_path)


def _write_shapefile(outpath, grid, catch_view):
    import fiona
    shapes = grid.polygonize(catch_view.astype(np.uint8))

    # Specify schema
    schema = {
        'geometry': 'Polygon',
        'properties': {'LABEL': 'float:16'}
    }

    # Write shapefile
    with fiona.open(str(outpath), 'w',
                    driver='ESRI Shapefile',
                    crs=grid.crs.srs,
                    schema=schema) as c:
        i = 0
        for shape, value in shapes:
            rec = {}
            rec['geometry'] = shape
            rec['properties'] = {'LABEL': str(value)}
            rec['id'] = str(i)
            c.write(rec)
            i += 1


def get_luggate_catchment_area(recalc=False):
    # did not work DEM is too coarse to easily create.
    if luggate_catch_area_path.exists() and not recalc:
        data = pd.read_csv(luggate_catch_area_path, index_col=0)
        return data

    dem_path = modelling_dir.joinpath('input_data/larger_area/8m_dem_luggate.tif')
    catchment_shapefile_dir = unbacked_dir.joinpath('input_data/lindis_luggate_catchments')
    catchment_shapefile_dir.mkdir(exist_ok=True, parents=True)
    from pysheds.grid import Grid
    grid = Grid.from_raster(str(dem_path))
    dem = grid.read_raster(str(dem_path))
    # Fill pits in DEM
    pit_filled_dem = grid.fill_pits(dem)

    # Fill depressions in DEM
    flooded_dem = grid.fill_depressions(pit_filled_dem)

    # Resolve flats in DEM
    inflated_dem = grid.resolve_flats(flooded_dem)
    print('dem conditioned')

    # Compute flow directions (d8)
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    fdir = grid.flowdir(inflated_dem, dirmap=dirmap)

    # Calculate flow accumulation
    acc = grid.accumulation(fdir, dirmap=dirmap)

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_alpha(0)
    plt.grid('on', zorder=0)
    im = ax.imshow(acc, extent=grid.extent, zorder=2,
                   cmap='cubehelix',
                   norm=LogNorm(1, acc.max()),
                   interpolation='bilinear')

    plt.colorbar(im, ax=ax, label='Upstream Cells')
    plt.title('Flow Accumulation', size=14)
    plt.xlabel('NZTMX')
    plt.ylabel('NZTMY')
    plt.tight_layout()
    plt.show()

    outdata = pd.DataFrame(columns=['raster_area', 'shp_area', 'px', 'py'])
    # Delineate a catchment
    # ---------------------
    # Specify pour point
    y, x = 5038214.22, 1304519.88  # luggate location
    name = 'luggate_at_sh6'
    print(name)
    outdata.loc[name, 'px'] = x
    outdata.loc[name, 'py'] = y

    # Snap pour point to high accumulation cell
    x_snap, y_snap = grid.snap_to_mask(acc > 1000, (x, y))

    # Delineate the catchment
    catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap,
                           xytype='coordinate')
    # calculate area
    cell_area = 8 * 8  # m2 from 8m dem
    catch_area = catch.sum() * cell_area
    outdata.loc[name, 'raster_area'] = catch_area

    # export shapefile to check
    grid2 = deepcopy(grid)
    grid2.clip_to(catch)
    catch_view = grid2.view(catch)
    _write_shapefile(outpath=catchment_shapefile_dir.joinpath(f'{name}.shp'), grid=grid2, catch_view=catch_view)
    t = gpd.read_file(catchment_shapefile_dir.joinpath(f'{name}.shp'))
    outdata.loc[name, 'shp_area'] = t.area.sum()

    outdata.to_csv(luggate_catch_area_path)


def get_lindis_area():
    t = gpd.read_file(processed_model_data_dir.joinpath('lindis_area_right.shp'))
    return t.area.sum()


def get_historical_flows(start_date, end_date, frequency='D'):
    outdata = pd.DataFrame(index=pd.date_range('1950-01-01', '2022-01-01', freq='D') + datetime.timedelta(hours=12))
    outdata.index.name = 'datetime'
    paths = [
        'streamflow_Lindis at Lindis Peak_data.csv',
        'streamflow_Luggate Creek at SH6 Bridge_data.csv',
        'streamflow_Grandview Creek at Lake Hawea Station_data.csv',
        'streamflow_Lagoon Creek at Mount Grand Station_data.csv',
    ]
    names = [
        'Lindis',
        'Luggate',
        'Grandview',
        'Lagoon',
    ]

    for p, n in zip(paths, names):
        df = pd.read_csv(base_model_data_dir.joinpath(p), skiprows=1)
        df.loc[:, 'datetime'] = pd.to_datetime(df.time)
        df.set_index('datetime', inplace=True)
        df.rename(columns={'streamflow': n}, inplace=True)

        outdata = pd.merge(outdata, df.loc[:, [n]], how='outer', left_index=True, right_index=True)

    outdata = outdata.dropna(how='all')

    ht = outdata.index
    if start_date is None:
        start_date = ht.min()
    if end_date is None:
        end_date = ht.max()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    idx = (outdata.index >= start_date) & (outdata.index <= end_date)
    outdata = outdata.loc[idx].resample(frequency).mean()
    return outdata


def compair_lindus_correlations():
    """
    did not use, moved to malf based approach
    :return:
    """
    from sklearn.linear_model import LinearRegression
    data = get_historical_flows(None, None, 'M')
    catchments = get_catchment_areas()
    all_catchments = {
        'Luggate': get_luggate_catchment_area().loc['luggate_at_sh6', 'shp_area'],
        'Grandview': catchments.loc['Grandview Creek', 'shp_area'],
        'Lagoon': catchments.loc['Lagoon Creek', 'shp_area'],
        'Lindis': get_lindis_area()
    }
    for k, v in all_catchments.items():
        data.loc[:, 'k'] *= 1 / v

    data.loc[:, 'month'] = data.index.month
    data.loc[np.in1d(data.month, [12, 1, 2]), 'season'] = 1  # summer
    data.loc[np.in1d(data.month, [3, 4, 5]), 'season'] = 2  # atumn
    data.loc[np.in1d(data.month, [6, 7, 8]), 'season'] = 3  # spring
    data.loc[np.in1d(data.month, [9, 10, 11]), 'season'] = 4  # winter

    stat_data = []
    predicted_rivers = [
        # 'Luggate',
        'Grandview',
        'Lagoon']
    predicted_colors = [
        # 'orange',
        'g',
        'r']
    for k in predicted_rivers:
        temp = data.loc[:, ['Lindis', 'month', 'season']]
        temp.loc[:, 'river'] = k
        temp.loc[:, 'catchment_area'] = all_catchments[k]
        temp.loc[:, 'flow'] = data.loc[:, k]
        stat_data.append(temp)
    stat_data = pd.concat(stat_data)

    fig, ax = plt.subplots()
    data.drop(columns=['month', 'season']).plot(ax=ax)
    fig, ax = plt.subplots()
    ax.scatter(data.loc[:, 'Lindis'], data.loc[:, 'Lagoon'], c='g', label='lagoon', s=data.loc[:, 'season'])
    ax.scatter(data.loc[:, 'Lindis'], data.loc[:, 'Luggate'], c='orange', label='luggate', s=data.loc[:, 'season'])
    ax.scatter(data.loc[:, 'Lindis'], data.loc[:, 'Grandview'], c='b', label='granview', s=data.loc[:, 'season'])
    ax.legend()

    fig, ax = plt.subplots()
    ax.set_title('catchment_area')
    ax.scatter(stat_data.loc[:, 'catchment_area'], stat_data.loc[:, 'flow'])
    fig, ax = plt.subplots()
    ax.scatter(stat_data.loc[:, 'season'], stat_data.loc[:, 'flow'])

    stat_data = stat_data.dropna(how='any')
    regr = LinearRegression()
    x = stat_data.loc[:, ['Lindis', 'catchment_area']]
    y = stat_data.loc[:, 'flow']
    regr.fit(x, y)
    print(regr.score(x, y))
    stat_data.loc[:, 'predict'] = regr.predict(x)
    fig, ax = plt.subplots()
    all_data = []
    for k, c in zip(predicted_rivers, predicted_colors):
        idx = stat_data.river == k
        x = stat_data.loc[idx, 'flow']
        y = stat_data.loc[idx, 'predict']
        ax.scatter(x, y, c=c, label=k)
        all_data.extend(x)
        all_data.extend(y)
    ax.plot([0, 1], [0, 1], c='k', ls=':')
    ax.legend()
    ax.set_ylim(min(all_data), max(all_data))
    ax.set_xlim(min(all_data), max(all_data))
    ax.set_aspect('equal')

    for k in predicted_rivers:
        temp = data.loc[:, ['Lindis']]
        temp.loc[:, 'catchment_area'] = all_catchments[k]
        data.loc[:, f'p_{k}'] = regr.predict(temp.loc[:, ['Lindis', 'catchment_area']])
    fig, ax = plt.subplots()
    ax.plot(data.index, data.Lindis, c='b', label='Lindis')
    for k, c in zip(predicted_rivers, predicted_colors):
        ax.plot(data.index, data.loc[:, k], c=c, label=k)
        ax.plot(data.index, data.loc[:, f'p_{k}'], c=c, label=f'p_{k}', ls='--')
    ax.legend()
    plt.show()


def calc_alf(data, key='flow'):
    data = data.copy(deep=True)
    data.loc[:, 'water_year'] = (data.index + pd.DateOffset(months=-6)).year
    data.loc[:, 'alf'] = data.loc[:, key].rolling(7).mean()
    out = data.groupby(['water_year']).min()

    return out


def lindis_correlation_with_malf():
    """
    this is the correct one for the hillslope data
    :param recalc:
    :return:
    """

    from sklearn.linear_model import LinearRegression
    data = get_historical_flows(None, None, 'D')
    data.loc[:, 'Lindis'] = data.loc[:, 'Lindis'].fillna(method='ffill')

    # data = data.resample('M').mean()
    catchments = get_catchment_areas()
    all_catchments = {
        'Luggate': get_luggate_catchment_area().loc['luggate_at_sh6', 'shp_area'],
        'Grandview': catchments.loc['Grandview Creek', 'shp_area'],
        'Lagoon': catchments.loc['Lagoon Creek', 'shp_area'],
        'Lindis': get_lindis_area()
    }
    colors = {
        'Luggate': 'orange',
        'Grandview': 'g',
        'Lagoon': 'r',
        'Lindis': 'b'
    }
    for k, v in all_catchments.items():
        data.loc[:, k] *= 1 / v

    fig, ax = plt.subplots()
    for k in all_catchments:
        c = colors[k]
        ax.plot(data.index, data.loc[:, k], c=c, label=k)
    ax.legend()
    ax.set_title('per catchment area')
    ax.set_ylabel('flow m3/s/catchment area')
    ax.set_xlabel('time')

    catchment_malfs = pd.DataFrame(columns=['malf', 'catchment_area'], dtype=float)
    alf_data = get_historical_flows(None, None)
    for k, v in all_catchments.items():
        alf_data.loc[:, k] *= 1 / v
    for k, v in all_catchments.items():
        if k == 'Luggate':
            continue
        temp = calc_alf(alf_data, k)
        catchment_malfs.loc[k, 'malf'] = temp.loc[:, 'alf'].mean()
        catchment_malfs.loc[k, 'catchment_area'] = v

    x = np.log(catchment_malfs.loc[:, 'catchment_area']).values[:, np.newaxis]
    y = catchment_malfs.loc[:, 'malf'].values
    regr_malf = LinearRegression()
    regr_malf.fit(x, y)
    print(regr_malf.score(x, y))
    xs = np.linspace(0, np.log(catchment_malfs.catchment_area).max(), 100)[:, np.newaxis]
    ys = regr_malf.predict(xs)
    xs2 = np.log(catchments.loc[:, 'shp_area'])[:, np.newaxis]
    ys2 = regr_malf.predict(xs2)

    fig, ax = plt.subplots()
    for k in all_catchments:
        if k == 'Luggate':
            continue
        ax.scatter(catchment_malfs.loc[k, 'catchment_area'], catchment_malfs.loc[k, 'malf'], label=k,
                   c=colors[k])
    ax.plot(np.e ** xs, ys, ls=':', c='k')
    ax.scatter(np.e ** xs2, ys2, c='pink')
    ax.legend()
    ax.set_ylabel('MALF (m3/day/catchment area)')
    ax.set_xlabel('catchment area')

    stat_data = []
    predicted_rivers = [
        # 'Luggate',
        'Grandview',
        'Lagoon']
    predicted_colors = [
        # 'orange',
        'g',
        'r']
    for k in predicted_rivers:
        temp = data.loc[:, ['Lindis']]
        temp.loc[:, 'river'] = k
        temp.loc[:, 'catchment_area'] = c = all_catchments[k]
        temp.loc[:, 'malf'] = regr_malf.predict(np.log([c])[:, np.newaxis])[0]
        temp.loc[:, 'flow'] = data.loc[:, k]
        stat_data.append(temp)
    stat_data = pd.concat(stat_data)

    stat_data = stat_data.dropna(how='any')
    regr = LinearRegression()
    x = stat_data.loc[:, ['Lindis', 'malf']]
    y = stat_data.loc[:, 'flow']
    regr.fit(x, y)
    print(regr.score(x, y))
    stat_data.loc[:, 'predict'] = regr.predict(x)
    fig, ax = plt.subplots()
    all_data = []
    for k in predicted_rivers:
        c = colors[k]
        idx = stat_data.river == k
        x = stat_data.loc[idx, 'flow']
        y = stat_data.loc[idx, 'predict']
        ax.scatter(x, y, c=c, label=k)
        all_data.extend(x)
        all_data.extend(y)
    ax.plot([0, 1], [0, 1], c='k', ls=':', label='1:1 line')
    ax.legend()
    ax.set_ylim(min(all_data), max(all_data))
    ax.set_xlim(min(all_data), max(all_data))
    ax.set_aspect('equal')
    ax.set_ylabel('predicted (flow/catchment area)')
    ax.set_xlabel('observed (flow/catchment area)')

    for k in all_catchments:
        temp = data.loc[:, ['Lindis']]
        temp.loc[:, 'malf'] = regr_malf.predict(np.log([[all_catchments[k]]]))[0]
        data.loc[:, f'p_{k}'] = regr.predict(temp.loc[:, ['Lindis', 'malf']])

    fig, ax = plt.subplots()
    for k in all_catchments:
        c = colors[k]
        ax.plot(data.index, data.loc[:, k], c=c, label=k)
        ax.plot(data.index, data.loc[:, f'p_{k}'], c=c, label=f'p_{k}', ls='--')
    ax.legend()
    ax.set_title('per catchment area')
    ax.set_ylabel('flow m3/s / catchment area')
    ax.set_xlabel('time')

    predictor = data.loc[:, ['Lindis']]
    for k, v in all_catchments.items():
        data.loc[:, k] *= v
        data.loc[:, f'p_{k}'] *= v

    fig, ax = plt.subplots()
    for k in all_catchments:
        c = colors[k]
        ax.plot(data.index, data.loc[:, k], c=c, label=k)
        ax.plot(data.index, data.loc[:, f'p_{k}'], c=c, label=f'p_{k}', ls='--')
    ax.legend()
    ax.set_title('flow')
    ax.set_ylabel('flow m3/s')
    ax.set_xlabel('time')

    outdata = pd.DataFrame(index=data.index, columns=catchments.index)
    for c in catchments.index:
        ca = catchments.loc[c, 'shp_area']
        temp = predictor.copy(deep=True)
        temp.loc[:, 'malf'] = regr_malf.predict(np.log([[ca]]))[0]
        outdata.loc[:, c] = regr.predict(temp.loc[:, ['Lindis', 'malf']]) * ca
    assert np.isclose(outdata.loc[:, 'Grandview Creek'], data.loc[:, 'p_Grandview']).all()

    # cull top flows
    outdata[outdata < 0] = 0  # get rid of predicted negative values
    temp = outdata.describe([0.9, 0.95, 0.97, 0.98, 0.99])
    print(temp)
    per = '98%'
    for k in outdata.keys():
        outdata.loc[outdata.loc[:, k] > temp.loc[per, k]] = temp.loc[per, k]
    outdata *= 86400  # convert from m3/s to m3/d

    grouped_data = pd.DataFrame(index=outdata.index)
    for g in catchments.loc[:, 'group'].unique():
        idxs = catchments.loc[catchments.group == g].index
        grouped_data.loc[:, g] = outdata.loc[:, idxs].sum(axis=1)
    fig, ax = plt.subplots()
    grouped_data.plot(ax=ax)
    ax.set_ylabel('flow m3/day')
    ax.set_xlabel('time')

    fig, ax = plt.subplots()
    (grouped_data / 86400).plot(ax=ax)
    ax.set_ylabel('flow m3/s')
    ax.set_xlabel('time')

    fig, ax = plt.subplots()
    (grouped_data / 86400 * 1000).plot(ax=ax)
    ax.set_ylabel('flow L/s')
    ax.set_xlabel('time')

    data = data.resample('M').mean()
    fig, ax = plt.subplots()
    all_data = []
    for k in predicted_rivers:
        c = colors[k]
        x = data.loc[:, k]
        y = data.loc[:, f'p_{k}']
        ax.scatter(x, y, c=c, label=k)
        all_data.extend(x)
        all_data.extend(y)
    ax.plot([0, 1], [0, 1], c='k', ls=':', label='1:1 line')
    ax.legend()
    ax.set_ylim(np.nanmin(all_data), np.nanmax(all_data))
    ax.set_xlim(np.nanmin(all_data), np.nanmax(all_data))
    ax.set_aspect('equal')
    ax.set_ylabel('predicted (flow)')
    ax.set_xlabel('observed (flow)')
    grouped_data.loc[:, 'year'] = grouped_data.index.year
    print(grouped_data.groupby('year').mean() / 365)

    print(grouped_data.mean())

    pass
    plt.show()
    # drop mt_brown
    outdata.drop(columns='ss22', inplace=True)
    return outdata


def get_hillside_flows(start_date, end_date, frequency='D', recalc=False):
    """
    get hillside flow records from start to end dates (inclusive),
     data is available from 2012-01-01 to 2021-12-31
    :param start_date: none or dates
    :param end_date: none or dates
    :param frequency: pd frequnecy code
    :return:
    """
    if flow_data_path.exists() and not recalc:
        data = pd.read_csv(flow_data_path)
        data.loc[:, 'datetime'] = pd.to_datetime(data.loc[:, 'datetime'])
        data.set_index('datetime', inplace=True)
        data = data.astype(float)
    else:
        data = lindis_correlation_with_malf()
        data.to_csv(flow_data_path)
    if start_date is None:
        start_date = data.index.min()
    if end_date is None:
        end_date = data.index.max()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    idx = (data.index >= start_date) & (data.index <= end_date)
    outdata = data.loc[idx].resample(frequency).mean()
    return outdata


if __name__ == '__main__':
    get_hillside_flows(None, None, recalc=True)
    get_hillside_catchment_locs(recalc=True)
