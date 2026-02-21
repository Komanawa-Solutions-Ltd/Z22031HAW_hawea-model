"""
created matt_dumont 
on: 2/21/26
"""
import numpy as np


def read_npz_spd(npz_path):
    """
    read in a stress period data file from an npz
    :param npz_path:
    :return: dict (stress period (int) -> np.recarry array)
    """
    with np.load(npz_path) as data:
        out = {int(k): data[k] for k in data.files}
    return out

def save_npz_spd(data, npz_path):
    """
    save a stress period data file to an npz
    :param data: dict (stress period (int) -> np.recarry array)
    :param npz_path:
    :return:
    """
    save_data = {str(k): v for k, v in data.items()}
    np.savez_compressed(npz_path, **save_data)
