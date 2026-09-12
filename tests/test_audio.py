import numpy as np

from speakmot.audio import Recorder


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
