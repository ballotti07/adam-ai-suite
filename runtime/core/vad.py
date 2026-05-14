import os
import torch
import onnxruntime as ort
import numpy as np

class Vad:
    def __init__(self, params=None):
        self.params = params or {}
        self.samplerate = self.params.get("samplerate", 16000)
        self.repo_or_dir = self.params.get("repo_or_dir", "snakers4/silero-vad")
        self.model_name = self.params.get("model_name", "silero_vad")
        self.force_reload = self.params.get("force_reload", False)
        self.use_onnx = self.params.get("use_onnx", False)
        self.no_voice_wait_sec = self.params.get("no_voice_wait_sec", 1)
        self.onnx_verbose = self.params.get("onnx_verbose", False)
        self.verbose = self.params.get("verbose", False)
        
        if self.use_onnx and not self.onnx_verbose:
            ort.set_default_logger_severity(3)
            
        try:
            hub_dir = torch.hub.get_dir()
            repo_dir_name = self.repo_or_dir.replace("/", "_") + "_master"
            local_repo_path = os.path.join(hub_dir, repo_dir_name)
            
            if os.path.exists(local_repo_path):
                print("[VAD] 🔍 Caricamento Silero VAD dalla cache locale")
                self.silero_vad_model, self.silero_utils = torch.hub.load(
                    repo_or_dir=local_repo_path,
                    model=self.model_name,
                    source='local', 
                    onnx=self.use_onnx,
                    verbose=self.verbose,
                )
            else:
                raise FileNotFoundError("Cache locale non trovata.")
                
        except Exception as e:
            print(f"[VAD] 🌐 Modello non trovato in locale. Scarico da GitHub...")
            self.silero_vad_model, self.silero_utils = torch.hub.load(
                repo_or_dir=self.repo_or_dir,
                model=self.model_name,
                force_reload=self.force_reload,
                onnx=self.use_onnx,
                trust_repo="check",
                verbose=self.verbose,
            )
        
        (self.get_speech_timestamps, self.save_audio, self.read_audio, 
         self.VADIterator, self.collect_chunks) = self.silero_utils
         
        self.no_voice_sec = 0
        self.audio_buffer = [] 
        
        self.vad_iterator = self.VADIterator(
            self.silero_vad_model,
            threshold=0.5,
            sampling_rate=self.samplerate,
            min_silence_duration_ms=100,
            speech_pad_ms=30,
        )

    def reset_vad(self):
        self.no_voice_sec = 0
        self.audio_buffer.clear()
        self.vad_iterator.reset_states()

    def check(self, mic_chunk, chunk_time):
        self.audio_buffer.extend(mic_chunk.tolist()) 
        window_size = 512
        result = "vad_continue"
        
        while len(self.audio_buffer) >= window_size:
            vad_window = np.array(self.audio_buffer[:window_size], dtype=np.float32)
            del self.audio_buffer[:window_size]
            
            window_time_sec = window_size / self.samplerate
            speech_dict = self.vad_iterator(vad_window, return_seconds=False)
            
            if speech_dict is not None:
                if "start" in speech_dict:
                    self.no_voice_sec = 0
                elif "end" in speech_dict:
                    self.no_voice_sec += window_time_sec
            else:
                if self.no_voice_sec != 0:
                    self.no_voice_sec += window_time_sec
                    if self.no_voice_sec > self.no_voice_wait_sec:
                        self.no_voice_sec = 0
                        self.vad_iterator.reset_states()
                        self.audio_buffer.clear()
                        return "vad_end"
                        
            if not self.vad_iterator.triggered:
                result = "None"
                
        return result