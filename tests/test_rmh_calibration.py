from pathlib import Path

from rmh_cal.calibration import compute_gradiometers, estimate_calibration, run_calibration
from rmh_io.sensors import MagnetometerReading


def make_readings(num_sensors: int = 4, samples: int = 5):
    readings = []
    for s in range(num_sensors):
        for t in range(samples):
            readings.append(
                MagnetometerReading(
                    sensor_id=f"sensor_{s}",
                    timestamp=float(t),
                    magnetic_field=(0.1 * s, 0.2 * s, 0.3 * s),
                )
            )
    return readings


def test_calibration_pipeline(tmp_path: Path):
    readings = make_readings()
    calibrations = estimate_calibration(readings)
    assert len(calibrations) == 4

    pairs = compute_gradiometers(calibrations)
    assert pairs[0][0] == "sensor_0"

    report = run_calibration(readings, tmp_path / "calibration.json")
    assert report.gradiometers == pairs
    assert (tmp_path / "calibration.json").exists()
