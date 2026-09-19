import numpy as np

from speakmot.audio import Recorder, normalize


def _feed(recorder: Recorder, amplitude: float, seconds: float) -> None:
    samples = int(recorder.sample_rate * seconds)
    chunk = np.full(samples, amplitude, dtype=np.float32)
    recorder.level = float(np.abs(chunk).max())
    recorder._track_silence(chunk)


def test_silence_alone_does_not_stop_recording():
    recorder = Recorder(sample_rate=16000)
    recorder.silence_stop = 1.0
    _feed(recorder, 0.0, 5.0)
    assert not recorder.silence_reached


def test_silence_after_speech_stops_recording():
    recorder = Recorder(sample_rate=16000)
    recorder.silence_stop = 1.0
    _feed(recorder, 0.4, 0.5)
    _feed(recorder, 0.0, 1.2)
    assert recorder.silence_reached


def test_pause_shorter_than_the_limit_is_ignored():
    recorder = Recorder(sample_rate=16000)
    recorder.silence_stop = 2.0
    _feed(recorder, 0.4, 0.5)
    _feed(recorder, 0.0, 0.9)
    _feed(recorder, 0.4, 0.3)
    _feed(recorder, 0.0, 0.9)
    assert not recorder.silence_reached


def test_disabled_auto_stop_never_triggers():
    recorder = Recorder(sample_rate=16000)
    recorder.silence_stop = 0.0
    _feed(recorder, 0.4, 0.5)
    _feed(recorder, 0.0, 10.0)
    assert not recorder.silence_reached


def test_quiet_recording_is_amplified():
    quiet = np.full(100, 0.1, dtype=np.float32)
    loud = normalize(quiet)
    assert abs(float(np.abs(loud).max()) - 0.9) < 1e-6


def test_loud_recording_is_left_alone():
    loud = np.full(100, 0.95, dtype=np.float32)
    assert np.array_equal(normalize(loud), loud)


def test_near_silence_is_not_amplified():
    silence = np.full(100, 0.001, dtype=np.float32)
    assert np.array_equal(normalize(silence), silence)


def test_empty_recording_is_returned_as_is():
    empty = np.zeros(0, dtype=np.float32)
    assert normalize(empty).size == 0


def test_snapshot_returns_audio_while_recording_continues():
    """Стриминг читает запись на ходу — забирать данные из буфера нельзя."""
    recorder = Recorder(sample_rate=16000)
    chunk = np.full(800, 0.3, dtype=np.float32)
    recorder._chunks = [chunk, chunk]

    first = recorder.snapshot()
    second = recorder.snapshot()

    assert first.size == 1600
    assert second.size == 1600


def test_snapshot_of_an_empty_recording():
    assert Recorder(sample_rate=16000).snapshot().size == 0
