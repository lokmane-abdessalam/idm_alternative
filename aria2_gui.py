#!/usr/bin/env python3
"""A lightweight graphical aria2 download manager for Fedora Linux."""
import os
import re
import signal
import shutil
import subprocess
import threading
import queue
import time
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "Aria2 Download Manager"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"
PROGRESS_RE = re.compile(
    r"\[#\S+\s+([0-9.]+(?:[KMGT]i?B|B))/([0-9.]+(?:[KMGT]i?B|B))"
    r"\((\d+)%\).*?DL:([0-9.]+(?:[KMGT]i?B|B))(?:\s+ETA:([^\]\s]+))?"
)

def human_bytes(value):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value or "—")
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if n < 1024 or unit == units[-1]:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n:.0f} B"
        n /= 1024
    return f"{n:.1f} TiB"

class DownloadJob:
    def __init__(self, app, url, folder, filename, connections, segments,
                 split_size, retries, user_agent, referer, resume):
        self.app = app
        self.id = uuid.uuid4().hex[:8]
        self.url = url
        self.folder = folder
        self.filename = filename
        self.connections = connections
        self.segments = segments
        self.split_size = split_size
        self.retries = retries
        self.user_agent = user_agent
        self.referer = referer
        self.resume = resume
        self.proc = None
        self.paused = False
        self.cancel_requested = False
        self.status = "Starting"
        self.progress = 0
        self.speed = "—"
        self.eta = "—"
        self.size = "—"
        self.name = filename or url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1] or url
        self.started_at = time.time()

    def command(self):
        cmd = [
            "aria2c",
            "--console-log-level=warn",
            "--summary-interval=1",
            "--show-console-readout=true",
            "--continue=" + ("true" if self.resume else "false"),
            "--auto-file-renaming=true",
            "--allow-overwrite=false",
            "--file-allocation=none",
            "--max-tries=" + str(self.retries),
            "--retry-wait=3",
            "--connect-timeout=30",
            "--timeout=60",
            "--max-connection-per-server=" + str(self.connections),
            "--split=" + str(self.segments),
            "--min-split-size=" + self.split_size,
            "--dir=" + str(self.folder),
        ]
        if self.filename:
            cmd.append("--out=" + self.filename)
        if self.user_agent.strip():
            cmd.append("--user-agent=" + self.user_agent.strip())
        if self.referer.strip():
            cmd.append("--referer=" + self.referer.strip())
        cmd.append(self.url)
        return cmd

class Aria2GUI:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1040x730")
        self.root.minsize(860, 620)
        self.events = queue.Queue()
        self.jobs = {}
        self._build_ui()
        self.root.after(200, self._process_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="Aria2 Download Manager", font=("TkDefaultFont", 17, "bold")).pack(side="left")
        ttk.Label(header, text="Multi-connection downloads for Fedora").pack(side="right", anchor="e")

        form = ttk.LabelFrame(outer, text="New download", padding=10)
        form.pack(fill="x", pady=(0, 10))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Download URL").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(form, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4)
        url_entry.focus_set()

        ttk.Label(form, text="File name (optional)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.filename_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.filename_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)

        ttk.Label(form, text="Save to folder").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.folder_var = tk.StringVar(value=str(DEFAULT_DOWNLOAD_DIR))
        ttk.Entry(form, textvariable=self.folder_var).grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)
        ttk.Button(form, text="Browse…", command=self._browse_folder).grid(row=2, column=3, padx=(8, 0), pady=4)

        options = ttk.Frame(form)
        options.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 2))
        for i in range(8):
            options.columnconfigure(i, weight=1 if i in (1, 3, 5, 7) else 0)

        ttk.Label(options, text="Connections").grid(row=0, column=0, sticky="w")
        self.connections_var = tk.IntVar(value=8)
        ttk.Spinbox(options, from_=1, to=16, width=5, textvariable=self.connections_var).grid(row=0, column=1, sticky="w", padx=(5, 12))
        ttk.Label(options, text="Segments").grid(row=0, column=2, sticky="w")
        self.segments_var = tk.IntVar(value=8)
        ttk.Spinbox(options, from_=1, to=16, width=5, textvariable=self.segments_var).grid(row=0, column=3, sticky="w", padx=(5, 12))
        ttk.Label(options, text="Min split size").grid(row=0, column=4, sticky="w")
        self.split_size_var = tk.StringVar(value="1M")
        ttk.Combobox(options, textvariable=self.split_size_var, values=["1M", "2M", "5M", "10M", "20M"], width=7, state="readonly").grid(row=0, column=5, sticky="w", padx=(5, 12))
        ttk.Label(options, text="Retries").grid(row=0, column=6, sticky="w")
        self.retries_var = tk.IntVar(value=5)
        ttk.Spinbox(options, from_=0, to=20, width=5, textvariable=self.retries_var).grid(row=0, column=7, sticky="w", padx=(5, 0))

        advanced = ttk.LabelFrame(form, text="Optional request headers", padding=(8, 4))
        advanced.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        advanced.columnconfigure(1, weight=1)
        advanced.columnconfigure(3, weight=1)
        ttk.Label(advanced, text="User-Agent").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.ua_var = tk.StringVar()
        ttk.Entry(advanced, textvariable=self.ua_var).grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=3)
        ttk.Label(advanced, text="Referer").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=3)
        self.referer_var = tk.StringVar()
        ttk.Entry(advanced, textvariable=self.referer_var).grid(row=0, column=3, sticky="ew", pady=3)

        self.resume_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Resume an existing partial download when possible", variable=self.resume_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(form, text="Start download", command=self._start_download).grid(row=5, column=3, sticky="e", pady=(8, 0))

        table_frame = ttk.LabelFrame(outer, text="Downloads", padding=8)
        table_frame.pack(fill="both", expand=True)
        columns = ("status", "progress", "speed", "eta", "folder")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="File")
        self.tree.heading("status", text="Status")
        self.tree.heading("progress", text="Progress")
        self.tree.heading("speed", text="Speed")
        self.tree.heading("eta", text="Time left")
        self.tree.heading("folder", text="Save location")
        self.tree.column("#0", width=230, minwidth=150)
        self.tree.column("status", width=105, anchor="center")
        self.tree.column("progress", width=95, anchor="center")
        self.tree.column("speed", width=100, anchor="e")
        self.tree.column("eta", width=85, anchor="center")
        self.tree.column("folder", width=240, minwidth=140)
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(10, 0))
        ttk.Button(controls, text="Pause", command=self._pause_selected).pack(side="left")
        ttk.Button(controls, text="Resume", command=self._resume_selected).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Cancel", command=self._cancel_selected).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Open save folder", command=self._open_folder).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Remove finished", command=self._remove_finished).pack(side="right")

        self.status_var = tk.StringVar(value="Ready. aria2c is required.")
        ttk.Label(outer, textvariable=self.status_var, anchor="w").pack(fill="x", pady=(8, 0))

    def _browse_folder(self):
        current = self.folder_var.get().strip() or str(DEFAULT_DOWNLOAD_DIR)
        folder = filedialog.askdirectory(initialdir=current, title="Choose download folder")
        if folder:
            self.folder_var.set(folder)

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror(APP_NAME, "Enter a download URL.")
            return
        if not re.match(r"^(https?|ftp|ftps|magnet):", url, re.IGNORECASE):
            messagebox.showerror(APP_NAME, "Please enter an HTTP, HTTPS, FTP or Magnet URL.")
            return
        folder_text = self.folder_var.get().strip()
        folder = Path(folder_text).expanduser() if folder_text else DEFAULT_DOWNLOAD_DIR
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if not folder.is_dir():
                raise OSError("The selected path is not a folder.")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Cannot use the save folder:\n{exc}")
            return
        filename = self.filename_var.get().strip()
        if filename:
            filename = Path(filename).name
            if filename in (".", ".."):
                messagebox.showerror(APP_NAME, "Please enter a valid file name.")
                return
        try:
            connections = max(1, min(16, int(self.connections_var.get())))
            segments = max(1, min(16, int(self.segments_var.get())))
            retries = max(0, min(20, int(self.retries_var.get())))
        except (ValueError, tk.TclError):
            messagebox.showerror(APP_NAME, "Connections, segments and retries must be numbers.")
            return
        if shutil.which("aria2c") is None:
            messagebox.showerror(APP_NAME, "aria2c was not found. Install it with:\nsudo dnf install aria2")
            return

        job = DownloadJob(
            self, url, folder, filename, connections, segments,
            self.split_size_var.get(), retries, self.ua_var.get(),
            self.referer_var.get(), self.resume_var.get()
        )
        self.jobs[job.id] = job
        self.tree.insert("", "end", iid=job.id, text=job.name,
                         values=(job.status, "0%", "—", "—", str(folder)))
        self.url_var.set("")
        self.filename_var.set("")
        self.status_var.set(f"Starting {job.name}…")
        threading.Thread(target=self._run_job, args=(job,), daemon=True).start()

    def _run_job(self, job):
        try:
            job.proc = subprocess.Popen(
                job.command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=0, start_new_session=True
            )
            self.events.put((job.id, "status", "Downloading"))
            buffer = bytearray()
            while True:
                chunk = job.proc.stdout.read(1)
                if not chunk:
                    break
                if chunk in (b"\r", b"\n"):
                    if buffer:
                        line = buffer.decode("utf-8", errors="replace")
                        self.events.put((job.id, "line", line))
                        buffer.clear()
                else:
                    buffer.extend(chunk)
            if buffer:
                self.events.put((job.id, "line", buffer.decode("utf-8", errors="replace")))
            code = job.proc.wait()
            self.events.put((job.id, "done", (code, job.cancel_requested)))
        except Exception as exc:
            self.events.put((job.id, "error", str(exc)))

    def _process_events(self):
        try:
            while True:
                job_id, kind, payload = self.events.get_nowait()
                job = self.jobs.get(job_id)
                if not job:
                    continue
                if kind == "status":
                    if not job.paused:
                        job.status = payload
                elif kind == "line":
                    match = PROGRESS_RE.search(payload)
                    if match:
                        done, total, percent, speed, eta = match.groups()
                        job.progress = int(percent)
                        job.size = f"{done}/{total}"
                        job.speed = speed + "/s"
                        job.eta = eta or "—"
                        if not job.paused:
                            job.status = "Downloading"
                elif kind == "done":
                    code, canceled = payload
                    if canceled:
                        job.status = "Canceled (partial kept)"
                    elif code == 0:
                        job.status = "Complete"
                        job.progress = 100
                        job.speed = "—"
                        job.eta = "—"
                    else:
                        job.status = f"Failed (code {code})"
                        job.speed = "—"
                        job.eta = "—"
                elif kind == "error":
                    job.status = "Error"
                    self.status_var.set(payload)
                self._update_row(job)
        except queue.Empty:
            pass
        active = sum(1 for j in self.jobs.values() if j.status in ("Starting", "Downloading", "Paused"))
        self.status_var.set(f"{active} active/paused download(s) · {len(self.jobs)} total")
        self.root.after(200, self._process_events)

    def _update_row(self, job):
        if self.tree.exists(job.id):
            self.tree.item(job.id, text=job.name,
                           values=(job.status, f"{job.progress}%", job.speed, job.eta, str(job.folder)))

    def _selected_job(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(APP_NAME, "Select a download first.")
            return None
        return self.jobs.get(selected[0])

    def _pause_selected(self):
        job = self._selected_job()
        if not job or not job.proc or job.proc.poll() is not None or job.paused:
            return
        try:
            os.killpg(job.proc.pid, signal.SIGSTOP)
            job.paused = True
            job.status = "Paused"
            self._update_row(job)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not pause download:\n{exc}")

    def _resume_selected(self):
        job = self._selected_job()
        if not job or not job.proc or job.proc.poll() is not None or not job.paused:
            return
        try:
            os.killpg(job.proc.pid, signal.SIGCONT)
            job.paused = False
            job.status = "Downloading"
            self._update_row(job)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not resume download:\n{exc}")

    def _cancel_selected(self):
        job = self._selected_job()
        if not job or not job.proc or job.proc.poll() is not None:
            return
        if not messagebox.askyesno(APP_NAME, "Cancel this download? Partial data will be kept when possible."):
            return
        job.cancel_requested = True
        try:
            if job.paused:
                os.killpg(job.proc.pid, signal.SIGCONT)
                job.paused = False
            job.proc.terminate()
            job.status = "Canceling…"
            self._update_row(job)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not cancel download:\n{exc}")

    def _open_folder(self):
        job = self._selected_job()
        if not job:
            return
        try:
            subprocess.Popen(["xdg-open", str(job.folder)])
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not open folder:\n{exc}")

    def _remove_finished(self):
        finished = {"Complete"}
        for job_id, job in list(self.jobs.items()):
            if job.status in finished or job.status.startswith("Failed") or job.status.startswith("Canceled") or job.status == "Error":
                if self.tree.exists(job_id):
                    self.tree.delete(job_id)
                del self.jobs[job_id]

    def _on_close(self):
        running = [j for j in self.jobs.values() if j.proc and j.proc.poll() is None]
        if running and not messagebox.askyesno(APP_NAME, "Downloads are running. Close the app anyway? Downloads will be stopped and partial files may be resumed later."):
            return
        for job in running:
            try:
                if job.paused:
                    os.killpg(job.proc.pid, signal.SIGCONT)
                job.proc.terminate()
            except OSError:
                pass
        self.root.destroy()

def main():
    if shutil.which("aria2c") is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, "aria2 is not installed.\n\nInstall it with:\nsudo dnf install aria2")
        root.destroy()
        return
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    Aria2GUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
