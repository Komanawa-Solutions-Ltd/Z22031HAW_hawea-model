"""
created matt_dumont 
on: 2/08/22
"""
from .hillside_inflows import get_hillside_catchment_locs, get_hillside_flows  # Finished
from .lake_data import get_lake_hawea_loc, get_lake_heads  # Finished
from .river_data import get_river_loc_data, get_river_stage_data  # Finished
from .irrigation_race_losses import get_race_locs, get_race_well_losses  # Finished
from .recharge_model import get_rch  # todo not finished, need to run soils and check results
from .get_pumping_data import get_historical_pumping_data, get_pumping_locs  # todo not finished, need to check data
from .all_wells import get_all_wells  # Finished


# todo make sure functions are in consistent fashion.