# Aria2 Download Manager for Fedora

A lightweight Tkinter graphical interface for `aria2c`, intended for Fedora Workstation.

## Features
- Paste an HTTP(S), FTP(S), or Magnet URL.
- Default destination: `~/Downloads`.
- Choose a destination folder and optional output filename.
- Configure connections per server, split count, minimum split size, and retry count.
- Optional User-Agent and Referer request headers.
- Progress, percentage, speed, ETA, and destination display.
- Pause, resume, cancel, open destination folder, and remove finished jobs.
- Uses aria2's continuation support for partial downloads.

## Install on Fedora
Extract the archive, open a terminal in the extracted folder, and run:

```bash
chmod +x install.sh
./install.sh
```

The installer uses `dnf` to install `aria2` and `python3-tkinter`, then adds an application launcher for your user account. It does not require running the app as root.

## Notes
- The default is 8 connections and 8 segments; some servers limit parallel connections. If a site behaves oddly, try 1–4.
- The server must support range requests for segmented downloads to reach their potential.
- Pause/resume uses process signals while the app is open. On cancellation or closing the app, aria2 is stopped and partial data is kept where possible; restart a download with the same URL, folder and filename to let aria2 attempt to resume.
- This is a small personal utility, not an official aria2 project.
- For torrents, magnet URLs are accepted; some torrent workflows may not have meaningful single-file output names.
