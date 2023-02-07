"""
created matt_dumont 
on: 7/02/23
"""
import tempfile
import time
from pathlib import Path
import py7zr

limit = 50  # limit in mb


def compress_model(indir, outdir):
    """
    compress a model so it is within the 50mb limit of github pushes
    :param indir:
    :param outdir:
    :return:
    """
    indir = Path(indir)
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)

    for f in indir.iterdir():
        if f.is_dir():
            outdir.joinpath(f.relative_to(indir)).mkdir()
        else:
            size = f.stat().st_size / (1024 * 1024)
            if size / 2 < limit:
                # compress assume roughly 50% compression
                compressed_path = outdir.joinpath(f.parent.relative_to(indir), f'{f.name}.7z')
                with py7zr.SevenZipFile(compressed_path, 'w', dereference=True) as archive:
                    print(f'zipping: {f.name}')
                    archive.write(f, arcname=f.name)
                # check size of new compressed file remove
                size = compressed_path.stat().st_size / (1024 * 1024)
                if size < limit:
                    continue
                compressed_path.unlink()
            # file is too big to compress... break into parts add compress
            base_out = outdir.joinpath(f.parent.relative_to(indir), f'{f.name}.7z')
            chunk_size = int(limit * .9 * (1024 * 1024))
            print(f'breaking and zipping: {f.name}')
            with f.open('rb') as opf:
                chunk = opf.read(chunk_size)
                i = 0

                while chunk:  # loop until the chunk is empty (the file is exhausted)
                    temp = Path(tempfile.mktemp())
                    with temp.open('wb') as tf:
                        tf.write(chunk)
                    with py7zr.SevenZipFile(base_out.parent.joinpath(f'{base_out.name}.{i:04d}'),
                                            'w', dereference=True) as archive:
                        archive.write(temp, arcname=f.name)
                    chunk = opf.read(chunk_size)  # read the next chunk
                    i += 1


def uncompress_model(indir, outdir):
    """
    undo the above compression so that the model can be easily run/imported to GUIs
    :param indir:
    :param outdir:
    :return:
    """
    indir = Path(indir)
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    paths = sorted(list(indir.iterdir()))
    suffixes = [e.name.split('.')[-1] for e in paths]
    joint_paths = []
    for p, suff in zip(paths, suffixes):
        if p.is_dir():
            outdir.joinpath(p.relative_to(indir)).mkdir(exist_ok=True)
        if suff == '7z':
            print(f'extracting: {p.name}')
            # simple un compressions
            with py7zr.SevenZipFile(p) as zfile:
                data = list(zfile.read().values())[0]
            new_file = outdir.joinpath(p.parent.relative_to(indir), p.name.replace('.7z', ''))
            with new_file.open('wb') as f:
                f.write(data.read())
        else:
            joint_paths.append(p)

    files = set([p.parent.joinpath('.'.join(p.name.split('.')[:-1])) for p in joint_paths])
    # split compressions
    for fname in files:
        print(f'extracting: {fname.name}')
        i = 0
        new_path = outdir.joinpath(fname.parent.relative_to(indir), fname.name.replace('.7z', ''))
        with new_path.open('wb') as f:
            zip_path = fname.parent.joinpath(f'{fname.name}.{i:04d}')
            while zip_path in paths:
                i += 1
                with py7zr.SevenZipFile(zip_path) as zfile:
                    data = list(zfile.read().values())[0]
                f.write(data.read())
                zip_path = fname.parent.joinpath(f'{fname.name}.{i:04d}')

def example():
    # compress_model('/home/matt_dumont/Downloads/Final_opt_model', '/home/matt_dumont/Downloads/Final_opt_model_comp')
    uncompress_model('/home/matt_dumont/Downloads/Final_opt_model_comp',
                     '/home/matt_dumont/Downloads/Final_opt_model_uncomp')
    ucomp = Path('/home/matt_dumont/Downloads/Final_opt_model_uncomp/')
    org = Path('/home/matt_dumont/Downloads/Final_opt_model/')
    for f in ucomp.iterdir():
        with f.open('rb') as file:
            new = file.read()
        with org.joinpath(f.name).open('rb') as ofile:
            old = ofile.read()
        assert new == old, f
    for f in org.iterdir():
        with f.open('rb') as file:
            new = file.read()
        with ucomp.joinpath(f.name).open('rb') as ofile:
            old = ofile.read()
        assert new == old, f


if __name__ == '__main__':
    compress_model('/home/matt_dumont/unbacked/hawea/3d_v1d/init_3d_v1d/Optimisations/Final_opt_model',
                   '/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/optimisation/final_opt_models/3d_v1d')
    compress_model('/home/matt_dumont/unbacked/hawea/3d_v1b/init_3d_v1b/Optimisations/Final_opt_model',
                   '/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/optimisation/final_opt_models/3d_v1b')
    compress_model('/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/Final_opt_model',
                   '/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/optimisation/final_opt_models/3d_v1a')