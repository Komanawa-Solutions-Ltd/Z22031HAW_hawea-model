"""
created matt_dumont 
on: 1/09/22
"""
# todo
from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs
from targets_and_sensitive_sites.head_targets import get_2011_piezo_survey
from targets_and_sensitive_sites.senstive_sites import get_wetlands

if __name__ == '__main__':
    get_riv_target_locs(recalc=True)
    get_2011_piezo_survey(recalc=True)
    get_wetlands(recalc=True)
