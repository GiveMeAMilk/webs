from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from relationship_viewer.models import RelationshipGraph
from relationship_viewer.store import load_graph
from relationship_viewer.ui import RelationshipViewer
from relationship_viewer.windowing import center_window


class StartupFrame(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=24)
        self.master = master
        self.grid(row=0, column=0, sticky="nsew")
        self._configure_window()
        self._build()

    def _configure_window(self) -> None:
        self.master.title("Relationship Viewer")
        self.master.minsize(360, 310)
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        center_window(self.master, 360, 210)

    def _build(self) -> None:
        ttk.Label(self, text="Relationship Viewer", font=("TkDefaultFont", 16, "bold")).grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 18),
        )
        ttk.Button(self, text="New Workspace", command=self.open_new).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=4,
        )
        ttk.Button(self, text="Open Example Workspace", command=self.open_example).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=4,
        )
        ttk.Button(self, text="Open Workspace", command=self.open_workspace).grid(
            row=3,
            column=0,
            sticky="ew",
            pady=4,
        )

        ttk.Button(self, text="Quit", command=self.master.destroy).grid(row=4, column=0, sticky="ew", pady=(16, 0))

    def open_example(self) -> None:
        self._open_viewer(load_graph(None), "Loaded sample workspace.")

    def open_workspace(self) -> None:
        filename = filedialog.askopenfilename(filetypes=[("Relationship JSON", "*.json"), ("All files", "*.*")])
        if not filename:
            return
        path = Path(filename)
        try:
            graph = load_graph(path)
        except (OSError, ValueError, KeyError) as error:
            messagebox.showerror("Open Workspace", f"Could not open {path.name}:\n{error}")
            return
        self._open_viewer(graph, f"Opened {path.name}.", path)

    def open_new(self) -> None:
        self._open_viewer(RelationshipGraph(), "Created blank workspace.")

    def _open_viewer(self, graph: RelationshipGraph, status_message: str, current_path: Path | None = None) -> None:
        self.destroy()
        RelationshipViewer(self.master, graph=graph, status_message=status_message, current_path=current_path)


def main() -> None:
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.2)
        ttk.Style(root).theme_use("clam")
    except tk.TclError:
        pass
    StartupFrame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
