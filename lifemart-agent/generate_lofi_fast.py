import numpy as np
import wave
import struct

SAMPLE_RATE = 44100
DURATION = 115.0  # 115 seconds
BPM = 82.0
BEAT_LEN = 60.0 / BPM
BAR_LEN = BEAT_LEN * 4.0

t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)
audio = np.zeros_like(t)

# Chords: Cmaj7 -> Am7 -> Dm7 -> G7
chords = [
    [261.63, 329.63, 392.00, 493.88], # Cmaj7
    [220.00, 261.63, 329.63, 392.00], # Am7
    [293.66, 349.23, 440.00, 523.25], # Dm7
    [196.00, 293.66, 349.23, 493.88], # G7
]
bass_notes = [130.81, 110.00, 146.83, 98.00]

bar_indices = (t // BAR_LEN).astype(int) % len(chords)
bar_time = t % BAR_LEN

# 1. Warm Rhodes Keys
for c_idx, chord in enumerate(chords):
    mask = (bar_indices == c_idx)
    bt = bar_time[mask]
    chord_sig = np.zeros_like(bt)
    env = np.exp(-0.85 * bt) * (1.0 - np.exp(-20.0 * bt))
    tremolo = 1.0 + 0.15 * np.sin(2.0 * np.pi * 4.5 * t[mask])

    for freq in chord:
        chord_sig += np.sin(2.0 * np.pi * freq * t[mask]) + 0.35 * np.sin(2.0 * np.pi * freq * 2.0 * t[mask]) + 0.1 * np.sin(2.0 * np.pi * freq * 3.0 * t[mask])

    audio[mask] += (chord_sig / len(chord)) * env * tremolo * 0.28

    # Bass
    bass_freq = bass_notes[c_idx]
    bass_env = np.exp(-1.1 * (bt % (BAR_LEN / 2.0)))
    bass_sig = (np.sin(2.0 * np.pi * bass_freq * t[mask]) + 0.25 * np.sin(2.0 * np.pi * bass_freq * 2.0 * t[mask])) * bass_env * 0.38
    audio[mask] += bass_sig

# 2. Vinyl texture
crackle = np.random.normal(0, 0.012, size=audio.shape)
audio += crackle

# 3. Drums
num_beats = int(DURATION / BEAT_LEN)
for beat in range(num_beats):
    beat_t = beat * BEAT_LEN
    beat_in_bar = beat % 4

    # Kick on 0 and 2.5
    for offset in ([0.0, 2.5 * BEAT_LEN] if beat_in_bar == 0 else []):
        start_idx = int((beat_t + offset) * SAMPLE_RATE)
        kick_len = int(SAMPLE_RATE * 0.22)
        end_idx = min(len(audio), start_idx + kick_len)
        if start_idx < len(audio):
            kt = np.linspace(0, (end_idx - start_idx) / SAMPLE_RATE, end_idx - start_idx, endpoint=False)
            k_freq = 130.0 * np.exp(-28.0 * kt) + 42.0
            kick = np.sin(2.0 * np.pi * k_freq * kt) * np.exp(-18.0 * kt) * 0.45
            audio[start_idx:end_idx] += kick

    # Snare on 1 and 3
    if beat_in_bar in [1, 3]:
        start_idx = int(beat_t * SAMPLE_RATE)
        snare_len = int(SAMPLE_RATE * 0.18)
        end_idx = min(len(audio), start_idx + snare_len)
        if start_idx < len(audio):
            st = np.linspace(0, (end_idx - start_idx) / SAMPLE_RATE, end_idx - start_idx, endpoint=False)
            noise = np.random.uniform(-1, 1, size=len(st)) * np.exp(-22.0 * st) * 0.28
            tone = np.sin(2.0 * np.pi * 180.0 * st) * np.exp(-35.0 * st) * 0.25
            audio[start_idx:end_idx] += (noise + tone)

    # Hi-hats with swing
    for h_off in [0.0, BEAT_LEN * 0.56]:
        start_idx = int((beat_t + h_off) * SAMPLE_RATE)
        hat_len = int(SAMPLE_RATE * 0.04)
        end_idx = min(len(audio), start_idx + hat_len)
        if start_idx < len(audio):
            ht = np.linspace(0, (end_idx - start_idx) / SAMPLE_RATE, end_idx - start_idx, endpoint=False)
            hat = np.random.uniform(-1, 1, size=len(ht)) * np.exp(-80.0 * ht) * 0.14
            audio[start_idx:end_idx] += hat

# Normalize
audio = audio / np.max(np.abs(audio)) * 0.88
int_audio = (audio * 32767.0).astype(np.int16)

with wave.open("/tmp/lofi_beat.wav", "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(int_audio.tobytes())

print("Fast Lo-Fi audio generated successfully!")
