"""
created matt_dumont 
on: 1/03/23
"""
from project_base import proj_root

# todo compare allocation scenarios,
#  long current vs current vs naturalised
outdir = proj_root.joinpath('Scenarios/allocation_results')
outdir.mkdir(exist_ok=True)

def compare_nat_opt_long(): # todo
    raise NotImplementedError

def compare_other_allocation_scens(): # todo
    raise NotImplementedError