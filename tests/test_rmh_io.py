from pathlib import Path

from rmh_io import AcquisitionPipeline, InMemoryBus, ParquetLogger, StreamDispatcher, build_synthetic_array


def test_acquisition_pipeline(tmp_path: Path):
    array = build_synthetic_array(2)
    bus = InMemoryBus(messages=[])
    dispatcher = StreamDispatcher(bus)
    logger = ParquetLogger(tmp_path / "capture.parquet", calibration={"gain": 1.0})
    pipeline = AcquisitionPipeline(array, dispatcher, logger)

    def fake_stream(duration_s: float, callback):
        for _ in range(3):
            callback(array.sample_once())

    array.stream = fake_stream  # type: ignore
    output = pipeline.run(duration_s=0.0)
    assert output.exists()
    assert logger.metadata_path.exists()
    assert bus.messages, "streaming should have produced bus messages"
