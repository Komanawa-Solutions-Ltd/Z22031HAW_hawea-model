"""
created matt_dumont 
on: 12/09/22
"""
import json
import geopandas as gpd
from tethysts import Tethys
import numpy as np
from pathlib import Path

if __name__ == '__main__':
    outdir = Path().home().joinpath('Downloads/era5_data')
    outdir.mkdir(exist_ok=True)
    geom = gpd.read_file(
        '/home/matt_dumont/Downloads/hawea_domain.shp'
    )
    geom = geom.to_json()
    ts = Tethys()
    datasets = ts.datasets
    my_dataset = [d for d in datasets if True
                  and (d['feature'] == 'atmosphere')
                  # and (d['owner'] == 'MET Norway')
                  and (d['method'] == 'simulation')
                  and (d['product_code'] == 'reanalysis-era5-land')
                  and (d['parameter'] in ['potential_et', 'reference_et', 'precipitation'])
                  ]
    for d in my_dataset:
        print(d)

    print(np.unique([e['owner'] for e in my_dataset]))
    print(np.unique([e['product_code'] for e in my_dataset]))
    ds_ids = [e['dataset_id'] for e in my_dataset]
    ps = [e['parameter'] for e in my_dataset]
    stations = []
    geom = json.loads(geom)
    geom = geom['features'][0]['geometry']
    for did, p in zip(ds_ids, ps):
        temp = ts.get_stations(did, geometry=geom)
        for e in temp:
            e['dataset_id'] = did
            e['parameter'] = p
        stations.extend([e for e in temp if e['time_range']['from_date'] < '1990-01-01'])
    use_stations = {}
    for s in stations:
        sid = s['station_id']
        if sid in use_stations:
            continue
        use_stations[sid] = s

    print(len(use_stations), 'stations')
    for s in use_stations.values():
        ks = ['station_id', 'name', 'parameter', 'time_range', 'dataset_id']
        print({k: s.get(k) for k in ks})
    pass
    for dsid, p in zip(ds_ids, ps):
        print(p)
        temp = ts.get_results(
            dataset_id=dsid,
            station_ids=list(use_stations.keys()),
            from_date='1950-01-01',
            to_date='2020-12-31',
            squeeze_dims=True
        )
        test = temp.resample(time='1D').sum()
        test.to_netcdf(outdir.joinpath(f'era5_{p}.nc'))
