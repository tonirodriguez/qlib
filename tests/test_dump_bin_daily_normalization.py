# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.dump_bin import DumpDataAll


class TestDumpDataDailyNormalization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="qlib_dump_norm_"))
        self.source_dir = self.temp_dir / "source"
        self.qlib_dir = self.temp_dir / "qlib"
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.qlib_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_daily_dump_ignores_intraday_timestamps(self):
        df = pd.DataFrame(
            {
                "date": [
                    "2026-03-02 00:00:00",
                    "2026-03-02 14:30:00",
                    "2026-03-03 00:00:00",
                    "2026-03-04 00:00:00",
                ],
                "symbol": ["TEST"] * 4,
                "close": [1.0, 1.1, 2.0, 3.0],
                "open": [1.0, 1.1, 2.0, 3.0],
                "high": [1.0, 1.1, 2.0, 3.0],
                "low": [1.0, 1.1, 2.0, 3.0],
                "volume": [10.0, 11.0, 20.0, 30.0],
            }
        )
        csv_path = self.source_dir / "TEST.csv"
        df.to_csv(csv_path, index=False)

        DumpDataAll(
            data_path=self.source_dir,
            qlib_dir=self.qlib_dir,
            include_fields="open,close,high,low,volume",
            max_workers=1,
        ).dump()

        calendar = pd.read_csv(self.qlib_dir / "calendars" / "day.txt", header=None).iloc[:, 0].tolist()
        self.assertEqual(calendar, ["2026-03-02", "2026-03-03", "2026-03-04"])

        close_bin = np.fromfile(self.qlib_dir / "features" / "test" / "close.day.bin", dtype="<f")
        self.assertEqual(int(close_bin[0]), 0)
        np.testing.assert_allclose(close_bin[1:], np.array([1.1, 2.0, 3.0], dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
