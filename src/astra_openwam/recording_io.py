"""Lossless observation NPZ compression; default delegates exactly to NumPy."""
import os
from pathlib import Path
import zipfile
import numpy as np


def savez_record(file, **arrays):
    level=int(os.environ.get('ROBODOJO_RECORD_COMPRESSION', '6'))
    if level == 6:
        return np.savez_compressed(file, **arrays)
    if level != 1:
        raise ValueError('Observation recording supports compression levels 1 or 6')
    path=os.fspath(file)
    if not path.endswith('.npz'):path += '.npz'
    # Same .npy representation, keys, dtypes and values. Only ZIP compression effort differs.
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,
                         compresslevel=1,allowZip64=True) as archive:
        for name, value in arrays.items():
            with archive.open(name+'.npy','w',force_zip64=True) as stream:
                np.lib.format.write_array(stream,np.asanyarray(value),allow_pickle=True)
