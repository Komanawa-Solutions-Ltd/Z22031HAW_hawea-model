"""
created matt_dumont 
on: 11/10/22
"""

import os
import shutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyemu
import flopy
import sys
from pathlib import Path
from optimisation.optimisation_period import start


def pest_from():
    temp_model_ws = Path.home().joinpath('Downloads/test_model')
    template_ws = Path.home().joinpath('Downloads/template')


    pf = pyemu.utils.PstFrom(
        original_d=temp_model_ws,
        new_d=template_ws,
        remove_existing=True,
        longnames=True,
        spatial_reference=None,
        zero_based=False,  # todo
        start_datetime='2015-07-18')

def raw_pest():

    # see https://github.com/pypest/pyemu/blob/develop/examples/modflow_to_pest_like_a_boss.ipynb

    # todo use optimisation/pest_run_data
    # todo I liek this better for the way that I expect to run the thing.
    raw_pst_dir = Path.home().joinpath('Downloads/raw_pst_trial')
    raw_pst_dir.mkdir(exist_ok=True)

    pst = pyemu.Pst(raw_pst_dir.joinpath('opt.pst'), load=False)
    pass

if __name__ == '__main__':
    raw_pest()
pass