# Relationship Viewer

A small Python/Tkinter desktop app for mapping people, organizations, social accounts, data sources, locations, and the relationships between them.

## Run

```bash
python3 app.py
```

Tkinter is included with most Python installations, so there are no package dependencies.
On launch, choose **Open Example Workspace**, **Open New Workspace**, or **Quit**.

## Features

- Tree view of entities and their linked relationships
- Canvas visualization with tree and radial layouts
- Add, edit, and delete entities
- Link entities with labeled relationships
- Search by name, type, notes, or attributes
- Workspace-level notes that save with the JSON file
- Save and open JSON workspaces
- Export the selected entity's relationship tree as text

## Data Format

Saved workspaces are plain JSON:

```json
{
  "notes": "Workspace notes for leads, questions, source quality, or next steps.",
  "entities": [
    {
      "id": "ent_alex",
      "name": "Alex Rivera",
      "type": "Person",
      "notes": "Primary person of interest.",
      "attributes": {
        "role": "Founder"
      }
    }
  ],
  "relationships": [
    {
      "id": "rel_1",
      "source": "ent_alex",
      "target": "ent_northstar",
      "label": "founded",
      "notes": ""
    }
  ]
}
```

Attribute fields in the GUI accept one `key: value` or `key=value` pair per line.
