"""
created matt_dumont 
on: 2/08/22
"""
from komanawa.hawea.model_build.supporting_data_analysis.hillside_inflows import get_hillside_catchment_locs, get_hillside_flows  # Finished
from komanawa.hawea.model_build.supporting_data_analysis.lake_data import get_lake_hawea_loc, get_lake_heads  # Finished
from komanawa.hawea.model_build.supporting_data_analysis.river_data import get_river_loc_data, get_river_stage_data, get_river_flow_data  # Finished
from komanawa.hawea.model_build.supporting_data_analysis.irrigation_race_losses import get_race_locs, get_race_well_losses  # Finished
from komanawa.hawea.model_build.supporting_data_analysis.recharge_model import get_rch, get_irrigation_code  # Finished
from komanawa.hawea.model_build.supporting_data_analysis.get_pumping_data import get_historical_pumping_data, get_pumping_locs, get_historical_full_allo_pumping_data, \
    get_historical_max_allo_pumping_data  # Finished
from komanawa.hawea.model_build.supporting_data_analysis.all_wells import get_all_wells  # Finished
