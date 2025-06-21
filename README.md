# Grafuria

Author: Saulo Popov Zambiasi  
E-mail: [saulopz@gmail.com](mailto:saulopz@gmail.com)

Created: 2024-10-25  
Last Update: 2025-06-20  
Version: 1.0

---

## About Grafuria

**Grafuria** is a graphical tool designed to create, visualize, and manipulate graphs using Lua or Python algorithms.

It allows users to easily construct directed and undirected graphs, assign weights to edges, and execute dynamic algorithms that interact with the graph in real time. Lua is used as the scripting language, and a subset of the API is also available in Python for reference.

![Screenshot](res/screenshot_001.png)

---

## Getting Started

### Launching from Command Line

To launch the program:

```sh
$ python3 main.py graph=graphs/dodecaedron.json script=scripts/bfs.lua
```

Or on Linux systems:

```sh
$ ./grafuria graph=... script=...
```

Both parameters are optional. If omitted, the interface will start with an empty canvas.

### Using the Interface

Within the graphical interface, you can:

* Open a graph by clicking the field next to `Graph`
* Load an algorithm by clicking the field next to `Algorithm`

### Toolbar Controls

* `Play`: Executes the selected algorithm on the current graph.
* `Stop`: Interrupts execution. Scripts should check `app:is_stopped()` periodically.
* `Refresh`: Clears the graph and logs. Interrupts the algorithm if it's running.

### Sidebar Controls

* `Animation`: Toggles visual feedback during execution.
* `Speed`: Adjusts execution speed (0 = slowest, 10 = instant).
* `Log Symbols`: Filters logs by prefix symbols in `app:log()` messages.

---

## Creating a Graph

When the program starts without arguments, you can build a new graph:

* **Mouse Button 2 (Middle Click)**: Add a vertex at the cursor position.
* **Mouse Button 1 (Left Click)**: Select a vertex or edge to configure its name or weight in the right sidebar.
* **Mouse Button 3 (Right Click)**: Connect a selected vertex A to another vertex B.

To save your graph: `File > Save...`
To start fresh: `File > New...`

---

## Writing Algorithms

Lua is the main scripting language used in Grafuria. Each algorithm script interacts with the graph via a globally available `app` instance.

> You may organize your scripts in subfolders under `lua/` for better modularity.

### Lua vs Python API Comparison

| Function          | Lua                        | Python                     |
| ----------------- | -------------------------- | -------------------------- |
| Logging           | `app:log("msg")`           | `app.log("msg")`           |
| Check Stop        | `app:is_stopped()`         | `app.is_stopped()`         |
| Set Solved        | `app:set_solved(true)`     | `app.set_solved(True)`     |
| Get Vertex Count  | `app:get_vertex_size()`    | `app.get_vertex_size()`    |
| Access Vertex     | `app:get_vertex(i)`        | `app.get_vertex(i)`        |
| Vertex by ID      | `app:get_vertex_by_id(id)` | `app.get_vertex_by_id(id)` |
| Wait Step         | `app:step()`               | `app.step()`               |
| Set/Get Variables | `app:set_var("k", v)`      | `app.set_var("k", v)`      |

Note: Lua arrays start at index 1, while Python uses index 0.

### Script Configuration Variables

Scripts may use a companion JSON file to define runtime parameters:

```json
{
  "deep": 5,
  "deep_min": 1,
  "deep_max": 10,
  "name": "Example Graph"
}
```

When loaded, the UI creates interactive fields for these variables. Ranges (`*_min` / `*_max`) create sliders.

The JSON file must have the same name as the script.

---

## Classes and Methods

### App Class

```lua
local size = app:get_vertex_size()
app:log("# Graph has " .. size .. " vertices.")
```

Available Methods:

* `log(message)` — Writes a log message to the application console.
* `is_stopped()` — Returns true if execution has been interrupted via the interface.
* `set_solved(bool)` — Marks the algorithm as completed or solved.
* `get_vertex_size()` — Returns the total number of vertices in the graph.
* `get_vertex(index)` — Returns the vertex at a given index.
* `get_vertex_by_id(id)` — Retrieves a vertex by its unique ID.
* `get_var(name)` — Retrieves a script variable defined in the configuration JSON.
* `set_var(name, value)` — Assigns a value to a script variable.
* `step()` — Causes the application to pause based on the speed setting, useful for animated execution steps.

### Vertex Class

```lua
local v = app:get_vertex(1)
if v then
    app:log("Vertex id: " .. v:get_id())
end
```

Available Methods:

* `get_id()` — Returns the vertex's unique ID.
* `get_name()` — Returns the name of the vertex.
* `get_state()` — Gets the current state of the vertex.
* `set_state(state)` — Sets the state of the vertex (e.g., `State.ACTIVE`).
* `get_edge_size()` — Returns the number of edges connected to this vertex.
* `get_edge(i)` — Returns the i-th edge of this vertex.
* `get_active_edge_size()` — Returns the number of edges currently in the `ACTIVE` state.
* `is_connected(vertex)` — Returns true if the current vertex is connected to the given vertex.
* `get_adjacent(edge)` — Returns the vertex connected to this one via the given edge.

### Edge Class

```lua
local edge = v:get_edge(1)
```

Available Methods:

* `get_id()` — Returns the edge's unique ID.
* `get_state()` / `set_state(state)` — Gets or sets the edge's state (e.g., active, testing).
* `get_weight()` / `set_weight(weight)` — Gets or sets the edge's weight (a floating-point value).
* `get_a()` — Returns one endpoint vertex of the edge.
* `get_b()` — Returns the other endpoint vertex of the edge.

---

### Vertex and Edge States

* `State.NONE`: Default state (not active)
* `State.TESTING`: Under evaluation
* `State.ACTIVE`: Marked as active during execution

---

## Examples

Sample content is available in the following folders:

* `graphs/` — includes examples like `dodecaedron.json`
* `scripts/` — includes BFS and DFS implementations

These scripts randomly choose two vertices and find paths using different strategies.

---

## Limitations and Future Work

* Bidirectional edges (A->B and B->A) are not supported in directed graphs.
* Self-loops (edges from a vertex to itself) are not yet implemented.
* There's currently no export option for saving the algorithm's result or final path.

---

For questions or contributions, feel free to contact the author or open a GitHub issue. Happy graphing!
