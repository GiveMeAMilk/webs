from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from relationship_viewer.layout import radial_positions, tree_positions
from relationship_viewer.models import ENTITY_TYPES, Entity, Relationship, RelationshipGraph
from relationship_viewer.store import export_tree_text, load_graph, parse_attributes, save_graph
from relationship_viewer.windowing import center_window


TYPE_COLORS = {
    "Person": "#2f6fed",
    "Organization": "#0f766e",
    "Social Account": "#9333ea",
    "Data Source": "#b45309",
    "Location": "#15803d",
    "Other": "#475569",
}


class RelationshipViewer(ttk.Frame):
    def __init__(
        self,
        master: tk.Tk,
        graph: RelationshipGraph | None = None,
        status_message: str = "Loaded sample workspace.",
    ) -> None:
        super().__init__(master, padding=10)
        self.master = master
        self.graph = graph if graph is not None else load_graph(None)
        self.current_path: Path | None = None
        self.selected_entity_id: str | None = next(iter(self.graph.entities), None)
        self.layout_mode = tk.StringVar(value="Tree")
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value=status_message)
        self.canvas_items: dict[int, str] = {}
        self.workspace_notes: tk.Text | None = None

        self._configure_window()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()
        self.refresh_all()

    def _configure_window(self) -> None:
        self.master.title("Relationship Viewer")
        self.master.minsize(920, 620)
        self.grid(row=0, column=0, sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        center_window(self.master, 1180, 760)

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(8, weight=1)

        ttk.Button(toolbar, text="New", command=self.new_workspace).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(toolbar, text="Open", command=self.open_workspace).grid(row=0, column=1, padx=4)
        ttk.Button(toolbar, text="Save", command=self.save_workspace).grid(row=0, column=2, padx=4)
        ttk.Button(toolbar, text="Save As", command=self.save_workspace_as).grid(row=0, column=3, padx=4)
        ttk.Separator(toolbar, orient="vertical").grid(row=0, column=4, sticky="ns", padx=8)
        ttk.Button(toolbar, text="Add Entity", command=self.add_entity).grid(row=0, column=5, padx=4)
        ttk.Button(toolbar, text="Add Link", command=self.add_relationship).grid(row=0, column=6, padx=4)
        ttk.Button(toolbar, text="Export Tree", command=self.export_tree).grid(row=0, column=7, padx=4)

        ttk.Label(toolbar, text="Search").grid(row=0, column=9, padx=(8, 4))
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=24)
        search.grid(row=0, column=10, sticky="e")
        search.bind("<KeyRelease>", lambda _event: self.refresh_tree())

        ttk.Label(toolbar, text="View").grid(row=0, column=11, padx=(12, 4))
        ttk.Combobox(
            toolbar,
            textvariable=self.layout_mode,
            values=("Tree", "Radial"),
            width=8,
            state="readonly",
        ).grid(row=0, column=12)
        self.layout_mode.trace_add("write", lambda *_args: self.draw_canvas())

    def _build_body(self) -> None:
        left = ttk.Frame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(left, columns=("type",), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Relationship Tree")
        self.tree.heading("type", text="Type")
        self.tree.column("#0", width=260, minwidth=220)
        self.tree.column("type", width=120, minwidth=100)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        center = ttk.Frame(self)
        center.grid(row=1, column=1, sticky="nsew")
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(center, bg="#f8fafc", highlightthickness=1, highlightbackground="#cbd5e1")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self.draw_canvas())
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        right = ttk.Frame(self, width=280)
        right.grid(row=1, column=2, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(right, text="Details", font=("TkDefaultFont", 13, "bold")).grid(row=0, column=0, sticky="w")
        self.details = tk.Text(right, width=34, height=18, wrap="word", state="disabled")
        self.details.grid(row=1, column=0, sticky="nsew", pady=(8, 8))

        actions = ttk.Frame(right)
        actions.grid(row=2, column=0, sticky="ew")
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(actions, text="Edit", command=self.edit_selected_entity).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(actions, text="Delete", command=self.delete_selected_entity).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(right, text="Links", font=("TkDefaultFont", 11, "bold")).grid(row=3, column=0, sticky="w", pady=(16, 4))
        self.links = tk.Listbox(right, height=9)
        self.links.grid(row=4, column=0, sticky="ew")

        ttk.Label(right, text="Workspace Notes", font=("TkDefaultFont", 11, "bold")).grid(row=5, column=0, sticky="w", pady=(16, 4))
        self.workspace_notes = tk.Text(right, width=34, height=8, wrap="word")
        self.workspace_notes.grid(row=6, column=0, sticky="ew")
        self.workspace_notes.bind("<KeyRelease>", lambda _event: self.sync_workspace_notes())
        self.workspace_notes.bind("<FocusOut>", lambda _event: self.sync_workspace_notes())

    def _build_statusbar(self) -> None:
        ttk.Label(self, textvariable=self.status_var, anchor="w").grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def refresh_all(self) -> None:
        self.refresh_tree()
        self.draw_canvas()
        self.refresh_details()
        self.refresh_workspace_notes()

    def refresh_workspace_notes(self) -> None:
        if self.workspace_notes is None:
            return
        self.workspace_notes.delete("1.0", tk.END)
        self.workspace_notes.insert("1.0", self.graph.notes)

    def sync_workspace_notes(self) -> None:
        if self.workspace_notes is None:
            return
        self.graph.notes = self.workspace_notes.get("1.0", tk.END).strip()

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        visible = {entity.id for entity in self.graph.filtered_entities(self.search_var.get())}
        roots = sorted(self.graph.entities.values(), key=lambda item: (item.type, item.name.lower()))
        for entity in roots:
            if entity.id in visible:
                self._insert_tree_entity("", entity.id, visible, set())
        if self.selected_entity_id:
            matches = self.tree.get_children("")
            for item in self.tree.get_children(""):
                if item.startswith(self.selected_entity_id):
                    self.tree.selection_set(item)
                    self.tree.see(item)
                    break

    def _insert_tree_entity(self, parent_item: str, entity_id: str, visible: set[str], seen: set[str]) -> None:
        entity = self.graph.entities[entity_id]
        item_id = f"{entity_id}:{len(seen)}:{parent_item or 'root'}"
        suffix = " (seen)" if entity_id in seen else ""
        self.tree.insert(parent_item, "end", iid=item_id, text=f"{entity.name}{suffix}", values=(entity.type,))
        if entity_id in seen:
            return
        next_seen = set(seen)
        next_seen.add(entity_id)
        for relationship, neighbor in self.graph.neighbors(entity_id):
            if neighbor.id not in visible and self.search_var.get().strip():
                continue
            relation_item = f"{relationship.id}:{item_id}"
            self.tree.insert(item_id, "end", iid=relation_item, text=f"-> {relationship.label}", values=("",))
            self._insert_tree_entity(relation_item, neighbor.id, visible, next_seen)

    def draw_canvas(self) -> None:
        self.canvas.delete("all")
        self.canvas_items.clear()
        width = max(self.canvas.winfo_width(), 600)
        height = max(self.canvas.winfo_height(), 420)
        if self.layout_mode.get() == "Radial":
            positions = radial_positions(self.graph, self.selected_entity_id, width, height)
        else:
            positions = tree_positions(self.graph, self.selected_entity_id, width, height)

        for relationship in self.graph.relationships.values():
            if relationship.source not in positions or relationship.target not in positions:
                continue
            x1, y1 = positions[relationship.source]
            x2, y2 = positions[relationship.target]
            self.canvas.create_line(x1, y1, x2, y2, fill="#94a3b8", width=2, arrow=tk.LAST)
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2 - 10, text=relationship.label, fill="#475569", font=("TkDefaultFont", 9))

        for entity_id, (x, y) in positions.items():
            entity = self.graph.entities[entity_id]
            color = TYPE_COLORS.get(entity.type, TYPE_COLORS["Other"])
            outline = "#0f172a" if entity_id == self.selected_entity_id else "#ffffff"
            oval = self.canvas.create_oval(x - 42, y - 30, x + 42, y + 30, fill=color, outline=outline, width=3)
            self.canvas_items[oval] = entity_id
            text = self.canvas.create_text(x, y, text=self._short_label(entity.name), fill="white", font=("TkDefaultFont", 10, "bold"), width=78)
            self.canvas_items[text] = entity_id

    def refresh_details(self) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", tk.END)
        self.links.delete(0, tk.END)
        entity = self.graph.entities.get(self.selected_entity_id or "")
        if not entity:
            self.details.insert("1.0", "Select an entity to see details.")
            self.details.configure(state="disabled")
            return
        lines = [entity.name, entity.type, "", entity.notes or "No notes.", ""]
        if entity.attributes:
            lines.append("Attributes")
            lines.extend(f"{key}: {value}" for key, value in entity.attributes.items())
        self.details.insert("1.0", "\n".join(lines))
        for relationship, neighbor in self.graph.neighbors(entity.id):
            self.links.insert(tk.END, f"{relationship.label}: {neighbor.name} ({neighbor.type})")
        self.details.configure(state="disabled")

    def on_tree_select(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        parts = selected[0].split(":", 1)
        if parts[0] in self.graph.entities:
            self.selected_entity_id = parts[0]
            self.draw_canvas()
            self.refresh_details()

    def on_canvas_click(self, event: tk.Event) -> None:
        item = self.canvas.find_closest(event.x, event.y)
        if item and item[0] in self.canvas_items:
            self.selected_entity_id = self.canvas_items[item[0]]
            self.refresh_all()

    def new_workspace(self) -> None:
        if not messagebox.askyesno("New workspace", "Start a blank workspace? Unsaved changes will be lost."):
            return
        self.graph = RelationshipGraph()
        self.current_path = None
        self.selected_entity_id = None
        self.status_var.set("Created blank workspace.")
        self.refresh_all()

    def open_workspace(self) -> None:
        filename = filedialog.askopenfilename(filetypes=[("Relationship JSON", "*.json"), ("All files", "*.*")])
        if not filename:
            return
        self.current_path = Path(filename)
        self.graph = load_graph(self.current_path)
        self.selected_entity_id = next(iter(self.graph.entities), None)
        self.status_var.set(f"Opened {self.current_path.name}.")
        self.refresh_all()

    def save_workspace(self) -> None:
        if self.current_path is None:
            self.save_workspace_as()
            return
        self.sync_workspace_notes()
        save_graph(self.graph, self.current_path)
        self.status_var.set(f"Saved {self.current_path.name}.")

    def save_workspace_as(self) -> None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Relationship JSON", "*.json"), ("All files", "*.*")],
        )
        if not filename:
            return
        self.current_path = Path(filename)
        self.save_workspace()

    def add_entity(self) -> None:
        dialog = EntityDialog(self.master, "Add Entity")
        if not dialog.result:
            return
        entity = Entity.create(dialog.result["name"], dialog.result["type"], dialog.result["notes"])
        entity.attributes = parse_attributes(dialog.result["attributes"])
        self.graph.add_entity(entity)
        self.selected_entity_id = entity.id
        self.status_var.set(f"Added {entity.name}.")
        self.refresh_all()

    def edit_selected_entity(self) -> None:
        entity = self.graph.entities.get(self.selected_entity_id or "")
        if not entity:
            return
        dialog = EntityDialog(self.master, "Edit Entity", entity)
        if not dialog.result:
            return
        entity.name = dialog.result["name"]
        entity.type = dialog.result["type"]
        entity.notes = dialog.result["notes"]
        entity.attributes = parse_attributes(dialog.result["attributes"])
        self.status_var.set(f"Updated {entity.name}.")
        self.refresh_all()

    def delete_selected_entity(self) -> None:
        entity = self.graph.entities.get(self.selected_entity_id or "")
        if not entity:
            return
        if not messagebox.askyesno("Delete entity", f"Delete {entity.name} and its relationships?"):
            return
        self.graph.remove_entity(entity.id)
        self.selected_entity_id = next(iter(self.graph.entities), None)
        self.status_var.set(f"Deleted {entity.name}.")
        self.refresh_all()

    def add_relationship(self) -> None:
        if len(self.graph.entities) < 2:
            messagebox.showinfo("Add Link", "Add at least two entities first.")
            return
        dialog = RelationshipDialog(self.master, self.graph)
        if not dialog.result:
            return
        try:
            relationship = Relationship.create(
                dialog.result["source"],
                dialog.result["target"],
                dialog.result["label"],
                dialog.result["notes"],
            )
            self.graph.add_relationship(relationship)
        except ValueError as error:
            messagebox.showerror("Invalid link", str(error))
            return
        self.status_var.set("Added relationship.")
        self.refresh_all()

    def export_tree(self) -> None:
        if not self.selected_entity_id:
            messagebox.showinfo("Export Tree", "Select an entity first.")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if not filename:
            return
        Path(filename).write_text(export_tree_text(self.graph, self.selected_entity_id), encoding="utf-8")
        self.status_var.set(f"Exported tree to {Path(filename).name}.")

    @staticmethod
    def _short_label(label: str) -> str:
        return label if len(label) <= 24 else label[:21] + "..."


class EntityDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Tk, title: str, entity: Entity | None = None) -> None:
        self.entity = entity
        self.result: dict[str, str] | None = None
        super().__init__(parent, title)

    def body(self, frame: ttk.Frame) -> tk.Widget:
        ttk.Label(frame, text="Name").grid(row=0, column=0, sticky="w", pady=4)
        self.name = ttk.Entry(frame, width=42)
        self.name.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Type").grid(row=1, column=0, sticky="w", pady=4)
        self.type = ttk.Combobox(frame, values=ENTITY_TYPES, state="readonly", width=39)
        self.type.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Notes").grid(row=2, column=0, sticky="nw", pady=4)
        self.notes = tk.Text(frame, width=42, height=5)
        self.notes.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Attributes").grid(row=3, column=0, sticky="nw", pady=4)
        self.attributes = tk.Text(frame, width=42, height=5)
        self.attributes.grid(row=3, column=1, sticky="ew", pady=4)

        if self.entity:
            self.name.insert(0, self.entity.name)
            self.type.set(self.entity.type)
            self.notes.insert("1.0", self.entity.notes)
            self.attributes.insert("1.0", "\n".join(f"{key}: {value}" for key, value in self.entity.attributes.items()))
        else:
            self.type.set("Person")
        return self.name

    def validate(self) -> bool:
        if not self.name.get().strip():
            messagebox.showerror("Missing name", "Name is required.")
            return False
        return True

    def apply(self) -> None:
        self.result = {
            "name": self.name.get().strip(),
            "type": self.type.get().strip() or "Other",
            "notes": self.notes.get("1.0", tk.END).strip(),
            "attributes": self.attributes.get("1.0", tk.END).strip(),
        }


class RelationshipDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Tk, graph: RelationshipGraph) -> None:
        self.graph = graph
        self.entity_names = {f"{entity.name} ({entity.type})": entity.id for entity in graph.entities.values()}
        self.result: dict[str, str] | None = None
        super().__init__(parent, "Add Link")

    def body(self, frame: ttk.Frame) -> tk.Widget:
        names = sorted(self.entity_names)
        ttk.Label(frame, text="From").grid(row=0, column=0, sticky="w", pady=4)
        self.source = ttk.Combobox(frame, values=names, state="readonly", width=44)
        self.source.grid(row=0, column=1, pady=4)
        ttk.Label(frame, text="To").grid(row=1, column=0, sticky="w", pady=4)
        self.target = ttk.Combobox(frame, values=names, state="readonly", width=44)
        self.target.grid(row=1, column=1, pady=4)
        ttk.Label(frame, text="Relationship").grid(row=2, column=0, sticky="w", pady=4)
        self.label = ttk.Entry(frame, width=47)
        self.label.grid(row=2, column=1, pady=4)
        ttk.Label(frame, text="Notes").grid(row=3, column=0, sticky="nw", pady=4)
        self.notes = tk.Text(frame, width=44, height=5)
        self.notes.grid(row=3, column=1, pady=4)
        if len(names) >= 2:
            self.source.set(names[0])
            self.target.set(names[1])
        self.label.insert(0, "related to")
        return self.label

    def validate(self) -> bool:
        if not self.source.get() or not self.target.get():
            messagebox.showerror("Missing endpoints", "Choose both endpoints.")
            return False
        if self.source.get() == self.target.get():
            messagebox.showerror("Invalid endpoints", "Choose two different entities.")
            return False
        return True

    def apply(self) -> None:
        self.result = {
            "source": self.entity_names[self.source.get()],
            "target": self.entity_names[self.target.get()],
            "label": self.label.get().strip() or "related to",
            "notes": self.notes.get("1.0", tk.END).strip(),
        }
