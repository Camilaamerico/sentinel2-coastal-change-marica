import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from water_mask import create_water_mask


def test_threshold_nodata_and_grid(tmp_path):
    source = tmp_path / "index.tif"
    target = tmp_path / "mask.tif"
    transform = from_origin(703470, 7458720, 10, 10)
    data = np.array([[-0.1, 0, 0.1], [np.nan, np.inf, -np.inf]], dtype="float32")
    with rasterio.open(source, "w", driver="GTiff", width=3, height=2,
                       count=1, dtype="float32", crs="EPSG:32723",
                       transform=transform, nodata=np.nan) as dst:
        dst.write(data, 1)
    create_water_mask(source, target)
    with rasterio.open(target) as result:
        np.testing.assert_array_equal(result.read(1), [[0, 0, 1], [255, 255, 255]])
        assert result.transform == transform
        assert result.crs.to_epsg() == 32723
        assert result.nodata == 255
