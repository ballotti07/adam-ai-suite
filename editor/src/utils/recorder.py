import pyaudio
import wave
import threading
import os

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames = []
        self.p = pyaudio.PyAudio()
        self.stream = None
        self._record_thread = None

    def start_recording(self):
        self.frames = []
        try:
            self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=24000,
                                      input=True, frames_per_buffer=1024)
            self.is_recording = True
            
            def _record():
                while self.is_recording:
                    try:
                        data = self.stream.read(1024, exception_on_overflow=False)
                        self.frames.append(data)
                    except Exception:
                        break
            
            self._record_thread = threading.Thread(target=_record, daemon=True)
            self._record_thread.start()
            return True
        except Exception:
            return False

    def stop_recording(self, output_filename):
        self.is_recording = False
        
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=1.0)
            
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        try:
            with wave.open(output_filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(24000)
                wf.writeframes(b''.join(self.frames))
            return True
        except Exception:
            return False
            
    def close(self):
        self.p.terminate()