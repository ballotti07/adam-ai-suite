import pyaudio
import numpy as np
import threading

class Mic:
    def __init__(self, params=None, vad_params=None):
        self.params = params or {}
        self.audio_device = self.params.get("audio_device")
        self.samplerate = self.params.get("samplerate")
        self.buffer_size = self.params.get("buffer_size")
        self.channels = self.params.get("channels")
        self.sample_format = pyaudio.paInt16
        self.bytes_per_second = (self.samplerate * 2 * self.channels)
        
        if self.audio_device == "default":
            self.audio_device = None
            
        self.vad_time = vad_params.get("no_voice_wait_sec") if vad_params else None
        self.lock = threading.Lock()
        
        p = pyaudio.PyAudio()
        self._stream = p.open(
            format=self.sample_format,
            channels=self.channels,
            rate=self.samplerate,
            frames_per_buffer=self.buffer_size,
            input=True,
            input_device_index=self.audio_device,
            stream_callback=self._callback,
            start=True,
        )
        
        self.max_len = self.bytes_per_second * 30
        self._chunk_buffer = bytes()
        self._empty_chunk_buffer = bytes(self.buffer_size * 2)
        
        self._recording_buffer = bytearray()
        self._muted = True

    def _callback(self, in_data, frame_count, time_info, status):
        with self.lock:
            if not self._muted:
                self._chunk_buffer = in_data
                self._recording_buffer.extend(in_data)
                
                excess = len(self._recording_buffer) - self.max_len
                if excess > 0:
                    del self._recording_buffer[:excess]
            else:
                self._chunk_buffer = in_data 
        return (in_data, pyaudio.paContinue)

    def mute(self):
        with self.lock:
            self._muted = True

    def unmute(self):
        with self.lock:
            self._recording_buffer.clear()
            self._chunk_buffer = bytes()
            self._muted = False

    def is_muted(self):
        return self._muted

    def get_recording(self):
        with self.lock:
            return bytes(self._recording_buffer)

    def get_chunk(self):
        if self._muted:
            return self._empty_chunk_buffer
        with self.lock:
            return self._chunk_buffer

    def start_mic(self):
        with self.lock:
            self._chunk_buffer = bytes()
            self._recording_buffer.clear()

    def stop_mic(self):
        with self.lock:
            self._muted = True

    def close(self):
        self.stop_mic()
        if hasattr(self, '_stream') and self._stream.is_active():
            self._stream.stop_stream()
            self._stream.close()

    def reset_recording(self):
        with self.lock:
            if len(self._recording_buffer) >= self.bytes_per_second:
                last_second = self._recording_buffer[-self.bytes_per_second:]
            else:
                last_second = self._recording_buffer[:]
            self._recording_buffer.clear() 
            self._recording_buffer.extend(last_second)