import io
import numpy as np


def convert_array_to_bytes(numpy_array):
    bytestream = io.BytesIO()
    np.save(bytestream, numpy_array)
    return bytestream.getvalue()


image = np.random.randint(0, 64000, (2048, 2048), np.uint16)
image_bytes = convert_array_to_bytes(image)