"""
created matt_dumont 
on: 13/09/22
"""
# keynote instructions for download: https://cds.climate.copernicus.eu/api-how-to
import cdsapi
from pathlib import Path

if __name__ == '__main__':
    c = cdsapi.Client()
    y = 1950
    c.retrieve(
        'reanalysis-era5-land',
        {
            'format': 'netcdf',
            'variable': ['potential_evaporation', 'total_precipitation'],
            'year': str(y),
            'month': [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
            ],
            'day': [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
                '13', '14', '15',
                '16', '17', '18',
                '19', '20', '21',
                '22', '23', '24',
                '25', '26', '27',
                '28', '29', '30',
                '31',
            ],
            'time': [
                '00:00', '01:00', '02:00',
                '03:00', '04:00', '05:00',
                '06:00', '07:00', '08:00',
                '09:00', '10:00', '11:00',
                '12:00', '13:00', '14:00',
                '15:00', '16:00', '17:00',
                '18:00', '19:00', '20:00',
                '21:00', '22:00', '23:00',
            ],
            'area': [
                -44.59, 169.17, -44.8,
                169.37,
            ],
        },
        Path.home().joinpath('Downloads', f'hawea_{y}.nc'))

    # todo do I need this????
