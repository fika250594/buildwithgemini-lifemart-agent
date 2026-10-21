import math
import struct
import wave
import random

SAMPLE_RATE = 44100
DURATION = 110.0  # 110 seconds to cover the demo video
BPM = 82
BEAT_LEN = 60.0 / BPM  # ~0.7317s per beat
BAR_LEN = BEAT_LEN * 4  # ~2.9268s per bar

def generate_lofi_track(filename):
    total_samples = int(SAMPLE_RATE * DURATION)
    audio = [0.0] * total_samples

    # Upbeat lo-fi jazz chord progression:
    # Cmaj7 (C4, E4, G4, B4) -> Am7 (A3, C4, E4, G4) -> Dm7 (D4, F4, A4, C5) -> G7sus4/G7 (G3, D4, F4, B4)
    chords = [
        [261.63, 329.63, 392.00, 493.88],       # Cmaj7
        [220.00, 261.63, 329.63, 392.00],       # Am7
        [293.66, 349.23, 440.00, 523.25],       # Dm7
        [196.00, 293.66, 349.23, 493.88],       # G7
    ]

    bass_notes = [130.81, 110.00, 146.83, 98.00] # C3, A2, D3, G2

    # 1. Generate Warm Electric Piano / Rhodes-style chords with gentle tremolo & lowpass vibe
    for i in range(total_samples):
        t = i / SAMPLE_RATE
        bar_idx = int(t / BAR_LEN) % len(chords)
        chord = chords[bar_idx]
        bar_time = t % BAR_LEN

        # Chord tone synthesis (warm organ/rhodes harmonics with soft attack)
        chord_val = 0.0
        env = math.exp(-0.8 * (bar_time % BAR_LEN)) * (1.0 - math.exp(-15.0 * (bar_time % BAR_LEN)))
        tremolo = 1.0 + 0.15 * math.sin(2.0 * math.pi * 4.5 * t)

        for freq in chord:
            # Fundamental + soft warm overtones
            tone = math.sin(2.0 * math.pi * freq * t) + \
                   0.4 * math.sin(2.0 * math.pi * freq * 2 * t) + \
                   0.15 * math.sin(2.0 * math.pi * freq * 3 * t)
            chord_val += tone

        chord_val = (chord_val / len(chord)) * env * tremolo * 0.28
        audio[i] += chord_val

        # Bass line (mellow sine bass)
        bass_freq = bass_notes[bar_idx]
        bass_env = math.exp(-1.2 * (bar_time % (BAR_LEN / 2)))
        bass_val = (math.sin(2.0 * math.pi * bass_freq * t) + 0.2 * math.sin(2.0 * math.pi * bass_freq * 2 * t)) * bass_env * 0.35
        audio[i] += bass_val

        # 2. Vinyl crackle / warm tape texture
        if random.random() < 0.002:
            audio[i] += (random.random() - 0.5) * 0.08
        audio[i] += (random.random() - 0.5) * 0.012

    # 3. Add chill bouncy Lo-Fi drum pattern (Kick on 1 & 3-and, Snare on 2 & 4, Hi-hats on 8ths with swing)
    for beat in range(int(DURATION / BEAT_LEN)):
        beat_time = beat * BEAT_LEN
        beat_in_bar = beat % 4

        # Kick on beat 0 and beat 2.5
        for k_offset in ([0.0, 2.5 * BEAT_LEN] if beat_in_bar == 0 else []):
            start_s = int((beat_time + k_offset) * SAMPLE_RATE)
            for j in range(int(SAMPLE_RATE * 0.22)):
                idx = start_s + j
                if idx < total_samples:
                    kt = j / SAMPLE_RATE
                    # Pitch sweep kick
                    k_freq = 130.0 * math.exp(-28.0 * kt) + 42.0
                    k_val = math.sin(2.0 * math.pi * k_freq * kt) * math.exp(-18.0 * kt) * 0.45
                    audio[idx] += k_val

        # Snare / rimshot on beats 1 and 3 (the 2nd and 4th beat of the bar)
        if beat_in_bar in [1, 3]:
            start_s = int(beat_time * SAMPLE_RATE)
            for j in range(int(SAMPLE_RATE * 0.18)):
                idx = start_s + j
                if idx < total_samples:
                    st = j / SAMPLE_RATE
                    noise = (random.random() - 0.5) * math.exp(-22.0 * st) * 0.28
                    tone = math.sin(2.0 * math.pi * 180.0 * st) * math.exp(-35.0 * st) * 0.25
                    audio[idx] += noise + tone

        # Swung Lo-Fi Hi-Hats on 8th notes
        for h_step in [0.0, BEAT_LEN * 0.56]: # light swing
            start_s = int((beat_time + h_step) * SAMPLE_RATE)
            for j in range(int(SAMPLE_RATE * 0.045)):
                idx = start_s + j
                if idx < total_samples:
                    ht = j / SAMPLE_RATE
                    hat = (random.random() - 0.5) * math.exp(-80.0 * ht) * 0.12
                    audio[idx] += hat

    # Normalize & soft clip
    max_amp = max(abs(x) for x in audio) or 1.0
    with wave.open(filename, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        for s in audio:
            norm = (s / max_amp) * 0.85
            clamped = max(-1.0, min(1.0, norm))
            int_val = int(clamped * 32767.0)
            wav.writeframes(struct.pack('<h', int_val))

if __name__ == "__main__":
    generate_lofi_track("/tmp/lofi_beat.wav")
    print("Lo-fi background music generated successfully at /tmp/lofi_beat.wav")
