"""
created matt_dumont 
on: 1/09/22
"""
# todo
from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs
from targets_and_sensitive_sites.head_targets import get_2011_piezo_survey, get_all_hds_targets
from targets_and_sensitive_sites.senstive_sites import get_wetlands
from targets_and_sensitive_sites.get_indicative_times import get_indicative_times_v2
from optimisation.optimisation_period import tdis

if __name__ == '__main__':
    get_2011_piezo_survey(recalc=True)
    get_wetlands(recalc=True)
    get_indicative_times_v2(recalc=True)
    get_all_hds_targets(tdis, recalc=True)
