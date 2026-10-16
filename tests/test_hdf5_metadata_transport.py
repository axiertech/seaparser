"""Logical attribute-only access is not a guarantee about transported bytes."""
from io import BytesIO
from struct import pack
import unittest

import h5py
import numpy as np


class TracedFile(BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.windows = []

    def readinto(self, buffer):
        start = self.tell()
        count = super().readinto(buffer)
        self.windows.append((start, start + count))
        return count


class HDF5MetadataTransportTests(unittest.TestCase):
    def test_compact_weather_values_share_attribute_read_window(self):
        # Synthetic HDF5 layout, not a claim about the actual producer files.
        values = np.array([17.125, 4.8125, 9.0625, 3.375], dtype='<f8')
        memory = BytesIO()
        with h5py.File(memory, 'w') as file:
            creation = h5py.h5p.create(h5py.h5p.DATASET_CREATE)
            creation.set_layout(h5py.h5d.COMPACT)
            dataset_id = h5py.h5d.create(file.id, b'VHM0', h5py.h5t.IEEE_F64LE,
                                       h5py.h5s.create_simple((4,)), dcpl=creation)
            dataset_id.write(h5py.h5s.ALL, h5py.h5s.ALL, values)
            dataset_id.close()
            file['VHM0'].attrs['units'] = 'm'
        data = memory.getvalue()
        pattern = pack('<4d', *values)
        offset = data.find(pattern)
        self.assertGreaterEqual(offset, 0)
        self.assertEqual(data.count(pattern), 1)
        source = TracedFile(data)
        with h5py.File(source, 'r') as file:
            self.assertEqual(file['VHM0'].attrs['units'], 'm')
            # No dataset values, coordinates, or slicing are requested here.
        self.assertTrue(any(start < offset + len(pattern) and offset < end
                            for start, end in source.windows))
