"""
created matt_dumont 
on: 22/12/22
"""

import sys
from pathlib import Path


if __name__ == '__main__':
    files = Path(sys.argv[1]).glob('**/*.*')
    for p in files:
        if p.is_dir():
            continue
        if p.name.split('.')[-1] in ['list', 'dat', 'png', 'p', 'log']:
            continue
        if p.name in ['param_overview.txt', 'mse.csv']:
            continue
        p.unlink()