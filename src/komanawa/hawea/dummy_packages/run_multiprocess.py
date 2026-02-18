"""
created matt_dumont 
on: 14/04/23
"""
import psutil
import multiprocessing
import logging
import os
import sys


def _start_process():
    """
    function to run at the start of each multiprocess sets the priority lower
    :return:
    """
    print('Starting', multiprocessing.current_process().name)
    p = psutil.Process(os.getpid())
    # set to lowest priority, this is windows only, on Unix use ps.nice(19)
    if sys.platform == "linux":
        p.nice(19)
        # linux
    elif sys.platform == "darwin":
        # OS X
        p.nice(19)
        raise NotImplementedError
    elif sys.platform == "win32":
        # Windows...
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    else:
        raise ValueError(f'unexpected platform: {sys.platform}')


def run_multiprocess(func, runs, logical=True, num_cores=None):
    """
    count the number of processors and then instiute the runs of a function to
    :param func: function with one argument kwargs.
    :param runs: a list of runs to pass to the function the function is called via func(kwargs)
    :param num_cores: int or None, if None then use all cores (+-logical) if int, set pool size to number of cores
    :param logical: bool if True then add the logical processors to the count
    :return:
    """
    assert isinstance(num_cores, int) or num_cores is None
    multiprocessing.log_to_stderr(logging.DEBUG)
    if num_cores is None:
        pool_size = psutil.cpu_count(logical=logical)
    else:
        pool_size = num_cores

    pool = multiprocessing.Pool(processes=pool_size,
                                initializer=_start_process,
                                )

    results = pool.map_async(func, runs)
    pool_outputs = results.get()
    pool.close()  # no more tasks
    pool.join()
    return pool_outputs
