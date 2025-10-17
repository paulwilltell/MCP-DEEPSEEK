import pytest

torch = pytest.importorskip("torch")

from rmh_inverse import RMHInversePINN, pinn_step, monte_carlo_uncertainty
from rmh_inverse.synthetic import dipole_phantom


def test_pinn_step_and_uncertainty():
    time_steps, grid_points, sensors = 4, 6, 2
    sensors_series, ecg, H_model = dipole_phantom(time_steps, grid_points, sensors)
    sensors_tensor = sensors_series.unsqueeze(0)  # batch=1
    ecg_tensor = ecg.unsqueeze(0)

    model = RMHInversePINN(sensor_dim=sensors * 3, grid_points=grid_points)
    losses = pinn_step(model, sensors_tensor, ecg_tensor, lambda x: H_model(x), dx=0.1)
    assert losses.total.item() > 0

    uncertainty = monte_carlo_uncertainty(model, sensors_tensor, ecg_tensor, samples=3)
    assert uncertainty.shape[0] == sensors_tensor.shape[0]
