import time
import pyaudio
import numpy as np
import queue
import threading

class Ap:
    def __init__(self, params=None):
        self.params = params or {}
        self.audio_device = self.params.get("audio_device")
        self.samplerate = self.params.get("samplerate", 24000)
        self.buffer_size = self.params.get("buffer_size", 960)
        self.channels = self.params.get("channels", 1)
        self.sample_format = pyaudio.paInt16

        if self.audio_device == "default":
            self.audio_device = None

        self.audio_queue = queue.Queue()
        self._playback_buffer = bytearray()

        self.finished_event = threading.Event()
        self.finished_event.set()
        self.is_playing = False

        p = pyaudio.PyAudio()
        self.stream = p.open(
            format=self.sample_format,
            channels=self.channels,
            rate=self.samplerate,
            frames_per_buffer=self.buffer_size,
            output=True,
            output_device_index=self.audio_device,
            stream_callback=self._callback,
        )

    def _callback(self, in_data, frame_count, time_info, status):
        expected_bytes = frame_count * self.channels * pyaudio.get_sample_size(self.sample_format)
        
        while len(self._playback_buffer) < expected_bytes:
            try:
                chunk = self.audio_queue.get_nowait()
                self._playback_buffer.extend(chunk)
                self.is_playing = True
            except queue.Empty:
                break
                
        if len(self._playback_buffer) >= expected_bytes:
            data = bytes(self._playback_buffer[:expected_bytes])
            del self._playback_buffer[:expected_bytes]
            if getattr(self, 'on_playback_chunk', None):
                arr = np.frombuffer(data, dtype=np.int16)
                if len(arr) > 0:
                    vol = np.sqrt(np.mean(np.square(arr.astype(np.float32))))
                    self.on_playback_chunk(vol)
        else:
            data = bytes(self._playback_buffer) + b'\x00' * (expected_bytes - len(self._playback_buffer))
            self._playback_buffer.clear()
            if self.is_playing:
                self.is_playing = False
                self.finished_event.set()
                if getattr(self, 'on_playback_chunk', None):
                    self.on_playback_chunk(0)
            
        return (data, pyaudio.paContinue)

    def check_audio_finished(self):
        self.finished_event.wait()
        
    def stream_sound(self, chunk):
        self.finished_event.clear()
        if isinstance(chunk, np.ndarray):
            chunk_bytes = chunk.tobytes()
        else:
            chunk_bytes = chunk
        self.audio_queue.put(chunk_bytes)

    def play_sound(self, sound):
        self.finished_event.clear()
        if isinstance(sound, np.ndarray):
            sound_bytes = sound.tobytes()
        else:
            sound_bytes = sound

        chunk_bytes_len = self.buffer_size * pyaudio.get_sample_size(self.sample_format) * self.channels
        
        for i in range(0, len(sound_bytes), chunk_bytes_len):
            chunk = sound_bytes[i : i + chunk_bytes_len]
            self.audio_queue.put(chunk)

    def close(self):
        self.is_playing = False
        self.finished_event.set()
        if hasattr(self, 'stream') and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()