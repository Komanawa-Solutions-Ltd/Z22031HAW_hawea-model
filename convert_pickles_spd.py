"""
This is included as a record of the process of converting pickled data files to npz files

created matt_dumont 
on: 2/21/26
"""
import pickle
from pathlib import Path
import numpy as np

from komanawa.hawea.io_utils import read_npz_spd


def convert_pickle_to_npz(pickle_path, reconvert=False):
    pickle_path = Path(pickle_path)
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)
    npz_path = pickle_path.with_suffix('.npz')
    if npz_path.exists() and not reconvert:
        return
    assert isinstance(data, dict), f'Expected data to be a dictionary, got {type(data)}'
    for k, v in data.items():
        if not isinstance(v, np.ndarray):
            raise AssertionError(f'Value for key {k} is not a numpy array: {type(v)}')
        assert isinstance(k, int) or isinstance(k, str), f'Expected key {k} to be an int or str, got {type(k)}'
    save_data = {str(k): v for k, v in data.items()}
    np.savez_compressed(npz_path, **save_data)



def check_data_spd(pickle_path):
    pickle_path = Path(pickle_path)
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)
    npz_path = pickle_path.with_suffix('.npz')
    if npz_path.exists():
        assert isinstance(data, dict), f'Expected data to be a dictionary, got {type(data)}'
        for k, v in data.items():
            if not isinstance(v, np.ndarray):
                raise AssertionError(f'Value for key {k} is not a numpy array: {type(v)}')
            assert isinstance(k, int) or isinstance(k, str), f'Expected key {k} to be an int or str, got {type(k)}'
        new_data = read_npz_spd(npz_path)
        assert set(new_data.keys()) == set(data.keys()), f'Keys in new data {set(new_data.keys())} do not match keys in old data {set(data.keys())}'
        for k in data.keys():
            assert data[k].dtype == new_data[k].dtype, f'Data types for key {k} do not match between old and new data: {data[k].dtype} vs {new_data[k].dtype}'
            if not np.array_equal(data[k], new_data[k]):
                if not np.allclose(data[k], new_data[k], equal_nan=True):  # catch a non-record array with nans
                    raise AssertionError(f'Values for key {k} do not match between old and new data')




if __name__ == '__main__':
    pickle_paths = list(Path('/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/src/komanawa/hawea').glob('**/*.p'))
    bad_sdp_paths = []
    for pickle_path in pickle_paths:
        try:
            convert_pickle_to_npz(pickle_path)
        except (AssertionError, ModuleNotFoundError) as e:
            bad_sdp_paths.append(pickle_path)
            print(f'Error converting {pickle_path}, skipping. Error: {e}')

    print('\n\n Checking data integrity for stress period data files...')
    nerrors = 0
    for pickle_path in pickle_paths:
        if pickle_path in bad_sdp_paths:
            continue
        try:
            check_data_spd(pickle_path)
        except Exception as e:
            print(f'Error checking data integrity for {pickle_path}, skipping. Error: {e}')
            nerrors += 1

    print(f'\n\nFinished checking data integrity. Number of errors: {nerrors}')