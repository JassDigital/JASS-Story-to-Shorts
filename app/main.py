import re
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
OUTPUT_DIR = ROOT / "output"
SPEECH_SCRIPT = APP_DIR / "synthesize_speech.ps1"


def make_captions(script, duration):
    words = re.findall(r"\S+", script.strip())
    if not words:
        raise ValueError("Please enter a script.")

    groups = [words[i:i + 6] for i in range(0, len(words), 6)]
    total_words = len(words)
    elapsed = 0.0
    entries = []

    for group in groups:
        start = elapsed
        elapsed += duration * len(group) / total_words
        entries.append((start, elapsed, " ".join(group)))

    def stamp(seconds):
        ms = int(round(seconds * 1000))
        hours, ms = divmod(ms, 3_600_000)
        minutes, ms = divmod(ms, 60_000)
        secs, ms = divmod(ms, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"

    return "\n\n".join(
        f"{i}\n{stamp(start)} --> {stamp(end)}\n{text}"
        for i, (start, end, text) in enumerate(entries, 1)
    ) + "\n"


def media_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("Could not read audio duration:\n" + result.stderr)
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Invalid audio duration returned by FFprobe.") from exc


class JASSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JASS Story-to-Shorts")
        self.root.geometry("800x760")
        self.root.minsize(660, 640)

        self.background = tk.StringVar()
        self.music_path = tk.StringVar()
        self.duration = tk.StringVar(value="30")
        self.narration_enabled = tk.BooleanVar(value=True)
        self.music_enabled = tk.BooleanVar(value=False)
        self.music_volume = tk.DoubleVar(value=15)
        self.status = tk.StringVar(value="Ready to create your Short.")

        main = ttk.Frame(root, padding=18)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main, text="JASS STORY-TO-SHORTS",
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w")

        ttk.Label(
            main,
            text="Create vertical story videos with narration and music.",
        ).pack(anchor="w", pady=(2, 12))

        ttk.Label(main, text="1. Background video").pack(anchor="w")
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(4, 10))
        ttk.Entry(row, textvariable=self.background).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(row, text="Browse...", command=self.browse_video).pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(main, text="2. Your script").pack(anchor="w")
        self.script = tk.Text(
            main, height=8, wrap="word",
            font=("Segoe UI", 11), undo=True
        )
        self.script.pack(fill="both", expand=True, pady=(4, 10))
        self.script.insert(
            "1.0",
            "Every great story begins with a moment that changes everything. "
            "Sometimes the smallest decision leads to the biggest adventure."
        )

        row = ttk.Frame(main)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Video duration:").pack(side="left")
        ttk.Combobox(
            row, textvariable=self.duration,
            values=("15", "30", "40", "60"),
            state="readonly", width=8
        ).pack(side="left", padx=8)
        ttk.Label(row, text="1080 × 1920 MP4").pack(
            side="left", padx=10
        )

        ttk.Checkbutton(
            main, text="Generate Windows voice narration",
            variable=self.narration_enabled
        ).pack(anchor="w", pady=(0, 8))

        ttk.Separator(main).pack(fill="x", pady=8)
        ttk.Label(
            main, text="3. Background music",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        ttk.Checkbutton(
            main, text="Add background music",
            variable=self.music_enabled
        ).pack(anchor="w", pady=(4, 5))

        row = ttk.Frame(main)
        row.pack(fill="x", pady=(0, 6))
        ttk.Entry(row, textvariable=self.music_path).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(row, text="Choose music...", command=self.browse_music).pack(
            side="left", padx=(8, 0)
        )

        row = ttk.Frame(main)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Music volume:").pack(side="left")
        self.volume_scale = ttk.Scale(
            row, from_=0, to=100, variable=self.music_volume,
            orient="horizontal"
        )
        self.volume_scale.pack(
            side="left", fill="x", expand=True, padx=10
        )
        self.volume_label = ttk.Label(row, text="15%")
        self.volume_label.pack(side="left")
        self.music_volume.trace_add(
            "write", lambda *_: self.volume_label.config(
                text=f"{round(self.music_volume.get())}%"
            )
        )

        ttk.Label(
            main,
            text="Music fades out at the end. Lower music volume to keep "
                 "narration clear.",
            wraplength=740
        ).pack(anchor="w", pady=(0, 10))

        self.render_button = ttk.Button(
            main, text="Create Short", command=self.render
        )
        self.render_button.pack(anchor="w", pady=(0, 10))

        ttk.Label(
            main, textvariable=self.status, wraplength=740
        ).pack(anchor="w")

    def browse_video(self):
        path = filedialog.askopenfilename(
            title="Select background video",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.mkv *.avi *.webm"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.background.set(path)

    def browse_music(self):
        path = filedialog.askopenfilename(
            title="Select background music",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.music_path.set(path)
            self.music_enabled.set(True)

    def render(self):
        background = Path(self.background.get())
        script = self.script.get("1.0", "end").strip()
        narrate = self.narration_enabled.get()
        use_music = self.music_enabled.get()
        music = Path(self.music_path.get()) if self.music_path.get().strip() else None

        if not background.is_file():
            messagebox.showerror(
                "Background required", "Please choose a valid background video."
            )
            return

        if not script:
            messagebox.showerror("Script required", "Please enter your script.")
            return

        if use_music and (music is None or not music.is_file()):
            messagebox.showerror(
                "Music required",
                "Enable background music and choose a valid audio file."
            )
            return

        if narrate and not SPEECH_SCRIPT.is_file():
            messagebox.showerror(
                "Speech helper missing",
                f"Cannot find:\n{SPEECH_SCRIPT}"
            )
            return

        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            messagebox.showerror(
                "FFmpeg tools missing",
                "Both ffmpeg and ffprobe must be available on PATH."
            )
            return

        try:
            duration = int(self.duration.get())
            volume = max(0.0, min(1.0, self.music_volume.get() / 100.0))
        except ValueError:
            messagebox.showerror("Invalid settings", "Check duration and volume.")
            return

        if use_music and volume <= 0:
            messagebox.showwarning(
                "Music volume is zero",
                "The music volume is set to zero. Increase it or disable music."
            )
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        destination = filedialog.asksaveasfilename(
            title="Save your Short",
            initialdir=str(OUTPUT_DIR),
            initialfile="jass_short.mp4",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
        )
        if not destination:
            return

        destination = Path(destination).resolve()
        if destination == background.resolve():
            messagebox.showerror(
                "Invalid output", "Output cannot overwrite the background video."
            )
            return
        if use_music and destination == music.resolve():
            messagebox.showerror(
                "Invalid output", "Output cannot overwrite the music file."
            )
            return

        self.render_button.config(state="disabled")
        self.status.set("Preparing audio and rendering video...")

        threading.Thread(
            target=self.render_worker,
            args=(str(background.resolve()), str(destination), duration,
                  script, narrate, str(music.resolve()) if use_music else None,
                  volume),
            daemon=True,
        ).start()

    def render_worker(
        self, background, destination, duration, script, narrate, music, volume
    ):
        destination = Path(destination)
        work_dir = destination.parent
        caption_file = work_dir / "captions_jass.srt"
        text_file = work_dir / "jass_narration.txt"
        wav_file = work_dir / "jass_narration.wav"

        try:
            audio_index = 1
            speech_length = None
            tempo = 1.0

            command = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", background]

            if narrate:
                text_file.write_text(script, encoding="utf-8-sig")
                self.root.after(
                    0, lambda: self.status.set(
                        "Generating Windows voice narration..."
                    )
                )

                speech = subprocess.run(
                    [
                        "powershell.exe", "-NoProfile",
                        "-ExecutionPolicy", "Bypass",
                        "-File", str(SPEECH_SCRIPT),
                        "-TextFile", str(text_file),
                        "-OutputWav", str(wav_file),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=300,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if speech.returncode != 0:
                    raise RuntimeError(
                        "Windows speech generation failed:\n"
                        + (speech.stderr or speech.stdout)[-3000:]
                    )
                if not wav_file.is_file() or wav_file.stat().st_size == 0:
                    raise RuntimeError("Speech generation produced no audio.")

                speech_length = media_duration(wav_file)
                if speech_length <= 0:
                    raise RuntimeError("Generated narration is empty.")

                ratio = speech_length / duration
                if ratio > 1.5:
                    raise RuntimeError(
                        f"Your narration is {speech_length:.1f} seconds, too long "
                        f"for a {duration}-second video. Shorten the script or "
                        "choose a longer duration."
                    )
                if ratio > 1.03:
                    tempo = ratio

                command.extend(["-i", str(wav_file)])
                audio_index += 1

            music_index = None
            if music:
                music_index = audio_index
                command.extend(["-stream_loop", "-1", "-i", music])

            caption_duration = (
                min(float(duration), speech_length)
                if narrate and speech_length is not None
                else float(duration)
            )
            captions = make_captions(script, caption_duration)
            caption_file.write_text(captions, encoding="utf-8-sig")

            self.root.after(
                0, lambda: self.status.set("Rendering vertical MP4 and mixing audio...")
            )

            command.extend([
                "-t", str(duration),
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,subtitles=captions_jass.srt",
                "-map", "0:v:0",
            ])

            fade_duration = min(2.0, float(duration))
            fade_start = max(0.0, float(duration) - fade_duration)

            if narrate and music:
                filters = (
                    f"[1:a]atempo={tempo:.5f},apad,"
                    f"atrim=duration={duration},asetpts=PTS-STARTPTS[narr];"
                    f"[{music_index}:a]volume={volume:.4f},"
                    f"afade=t=out:st={fade_start}:d={fade_duration},"
                    f"atrim=duration={duration},asetpts=PTS-STARTPTS[mus];"
                    "[narr][mus]amix=inputs=2:duration=first:"
                    "dropout_transition=2[aout]"
                )
                command.extend([
                    "-filter_complex", filters,
                    "-map", "[aout]",
                ])
            elif narrate:
                command.extend([
                    "-map", "1:a:0",
                    "-af",
                    f"atempo={tempo:.5f},apad,atrim=duration={duration}",
                ])
            elif music:
                command.extend([
                    "-map", f"{music_index}:a:0",
                    "-af",
                    f"volume={volume:.4f},"
                    f"afade=t=out:st={fade_start}:d={fade_duration},"
                    f"atrim=duration={duration}",
                ])
            else:
                command.append("-an")

            if narrate or music:
                command.extend(["-c:a", "aac", "-b:a", "192k"])

            command.extend([
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(destination),
            ])

            result = subprocess.run(
                command,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=1800,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            if result.returncode != 0:
                raise RuntimeError(
                    "FFmpeg rendering failed:\n" + result.stderr[-3500:]
                )

            if not destination.is_file() or destination.stat().st_size == 0:
                raise RuntimeError("FFmpeg did not produce an output video.")

            self.root.after(0, lambda: self.finished(True, str(destination)))

        except Exception as exc:
            error = str(exc)
            self.root.after(0, lambda e=error: self.finished(False, e))
        finally:
            for path in (caption_file, text_file, wav_file):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    def finished(self, success, result):
        self.render_button.config(state="normal")
        if success:
            self.status.set("Video created successfully.")
            messagebox.showinfo(
                "JASS Story-to-Shorts",
                f"Your video is ready:\n{result}"
            )
        else:
            self.status.set("Rendering failed. See the error message.")
            messagebox.showerror("Rendering failed", result)


if __name__ == "__main__":
    window = tk.Tk()
    JASSApp(window)
    window.mainloop()
