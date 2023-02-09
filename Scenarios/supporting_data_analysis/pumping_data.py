"""
created matt_dumont 
on: 9/02/23
"""

accepted_pump_names = (  # todo more pumping scenarios??
    'no_pump',
)


def get_scen_pumping_data(pump_name, tdis, recalc=False):
    """
    get pumping stress period data for scenarios
    :param pump_name: defined pumping name see 'accepted_pump_names'
    :param tdis: time distritisation object
    :param recalc: bool recalc from dataset
    :return:
    """
    assert pump_name in accepted_pump_names, f'unknown pump name: {pump_name}, expected on of: {accepted_pump_names}'
    if pump_name == 'no_pump':
        return {}
    else:
        raise NotImplementedError(f'shouldnt get here unless {pump_name} is not fully implemented')


def data_checks():  # todo and plot spd (or similar) and save
    from Scenarios.scen_period import scen_tdis
    for n in accepted_pump_names:
        if n == 'no_pump':
            continue
        data = get_scen_pumping_data(n, scen_tdis)

    raise NotImplementedError
