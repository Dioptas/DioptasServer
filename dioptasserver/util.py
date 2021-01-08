import io
import numpy as np


def convert_array_to_bytes(numpy_array):
    bytestream = io.BytesIO()
    np.save(bytestream, numpy_array)
    return bytestream.getvalue()
