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


## Custom PNG icon
To use your `downloads-icon-android-lollipop.png` logo, place the PNG either:
- next to `install.sh` in the extracted project folder, or
- in `~/Downloads/`.

Then run `./install.sh` again. The installer copies the PNG into the app's user-local installation folder, uses it for the GNOME application launcher, and the app uses it as its window icon. If the image is not found, installation still succeeds with a default icon.

## Uninstall the application

To uninstall Aria2 Download Manager from Fedora, open a terminal and run:

```bash
rm -rf ~/.local/share/aria2-download-manager
rm -f ~/.local/share/applications/aria2-download-manager.desktop
```

This removes the application files and its GNOME application launcher.

**Note:** This command does not delete downloaded files in `~/Downloads`, nor does it uninstall `aria2`, Python, or other dependencies installed by the installer.

### Optional: Remove dependencies

If you installed `aria2` and `python3-tkinter` specifically for this application and no longer need them, you can remove them with:

```bash
sudo dnf remove aria2 python3-tkinter
```

**Warning:** Only remove these dependencies if no other applications rely on them.
