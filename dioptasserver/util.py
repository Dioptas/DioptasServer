import io
import asyncio
import numpy as np
from asyncio.coroutines import iscoroutine


def convert_array_to_bytes(numpy_array):
    bytestream = io.BytesIO()
    np.save(bytestream, numpy_array)
    return bytestream.getvalue()


image = np.random.randint(0, 64000, (2048, 2048), np.uint16)
image_bytes = convert_array_to_bytes(image)


def run_coroutine(coroutine):
    if iscoroutine(coroutine):
        asyncio.run_coroutine_threadsafe(coroutine, asyncio.get_event_loop())
