// Package graph is the graph model of Grafuria: vertices, edges, their
// states, and the JSON file format. It knows nothing about interfaces.
//
// A Graph is not safe for concurrent use. While a script runs, only the
// script goroutine touches the graph; everyone else learns about changes
// through the Listener, which receives each change with its new state,
// so nobody needs to read the graph concurrently.
package graph

import (
	"encoding/json"
	"errors"
	"fmt"
	"math/rand"
	"os"
)

// State of a vertex or edge during an execution. Scripts see these values.
type State int

const (
	None    State = 0
	Active  State = 1
	Testing State = 2
	Scout   State = 3
	Invalid State = 4
)

// Kind tells whether a Change is about a vertex or an edge.
type Kind int

const (
	VertexKind Kind = iota
	EdgeKind
)

// Change reports that an element took a new state.
type Change struct {
	Kind  Kind
	ID    int
	State State
}

// Vertex of the graph.
type Vertex struct {
	ID    int
	Name  string
	X, Y  float64
	State State
	// Edges connected to this vertex. The order matters: it is the
	// traversal order seen by scripts.
	Edges []*Edge
	// Vars holds free values that scripts attach to the vertex.
	Vars map[string]any

	neighbor    map[int]*Edge // edge to each adjacent vertex, by vertex id
	activeEdges int
	graph       *Graph
}

// Edge connects vertices A and B. It is stored in the edge lists of both
// ends, so scripts can traverse it from either one. In a directed graph
// (Bidirectional false) the direction A -> B is only drawn.
type Edge struct {
	ID     int
	A, B   *Vertex
	Weight float64
	State  State

	graph *Graph
}

// Graph holds vertices and edges in insertion order.
type Graph struct {
	Bidirectional bool
	Vertices      []*Vertex
	Edges         []*Edge
	// Listener, if set, is called on every state change.
	Listener func(Change)

	vertexByID map[int]*Vertex
	edgeByID   map[int]*Edge
	nextVertex int
	nextEdge   int
}

// Errors returned when editing.
var (
	ErrDuplicateID = errors.New("duplicated id")
	ErrLoop        = errors.New("loops (edges from a vertex to itself) are not supported")
	ErrConnected   = errors.New("vertices are already connected")
	ErrNotFound    = errors.New("element not found")
)

// New returns an empty graph.
func New(bidirectional bool) *Graph {
	return &Graph{
		Bidirectional: bidirectional,
		vertexByID:    map[int]*Vertex{},
		edgeByID:      map[int]*Edge{},
	}
}

func (g *Graph) notify(c Change) {
	if g.Listener != nil {
		g.Listener(c)
	}
}

// ---------------------------------------------------------------- vertices

// AddVertex adds a vertex with the next free id.
func (g *Graph) AddVertex(name string, x, y float64) *Vertex {
	v, _ := g.AddVertexWithID(g.nextVertex, name, x, y)
	return v
}

// AddVertexWithID adds a vertex with a given id (used when loading files).
func (g *Graph) AddVertexWithID(id int, name string, x, y float64) (*Vertex, error) {
	if _, taken := g.vertexByID[id]; taken {
		return nil, fmt.Errorf("vertex %d: %w", id, ErrDuplicateID)
	}
	v := &Vertex{
		ID: id, Name: name, X: x, Y: y,
		Vars:     map[string]any{},
		neighbor: map[int]*Edge{},
		graph:    g,
	}
	g.Vertices = append(g.Vertices, v)
	g.vertexByID[id] = v
	if id >= g.nextVertex {
		g.nextVertex = id + 1
	}
	return v, nil
}

// RemoveVertex removes a vertex and every edge connected to it.
func (g *Graph) RemoveVertex(v *Vertex) {
	for len(v.Edges) > 0 {
		g.RemoveEdge(v.Edges[0])
	}
	g.Vertices = without(g.Vertices, v)
	delete(g.vertexByID, v.ID)
}

// Vertex returns the vertex at position index (0-based), or nil.
func (g *Graph) Vertex(index int) *Vertex {
	if index < 0 || index >= len(g.Vertices) {
		return nil
	}
	return g.Vertices[index]
}

// VertexByID returns the vertex with this id, or nil.
func (g *Graph) VertexByID(id int) *Vertex { return g.vertexByID[id] }

// ---------------------------------------------------------------- edges

// AddEdge connects a and b with the next free id.
func (g *Graph) AddEdge(a, b *Vertex, weight float64) (*Edge, error) {
	return g.AddEdgeWithID(g.nextEdge, a, b, weight)
}

// AddEdgeWithID connects a and b with a given id (used when loading files).
func (g *Graph) AddEdgeWithID(id int, a, b *Vertex, weight float64) (*Edge, error) {
	switch {
	case a == b:
		return nil, ErrLoop
	case a.IsConnected(b):
		return nil, fmt.Errorf("vertices %d and %d: %w", a.ID, b.ID, ErrConnected)
	}
	if _, taken := g.edgeByID[id]; taken {
		return nil, fmt.Errorf("edge %d: %w", id, ErrDuplicateID)
	}
	e := &Edge{ID: id, A: a, B: b, Weight: weight, graph: g}
	g.Edges = append(g.Edges, e)
	g.edgeByID[id] = e
	a.Edges = append(a.Edges, e)
	b.Edges = append(b.Edges, e)
	a.neighbor[b.ID] = e
	b.neighbor[a.ID] = e
	if id >= g.nextEdge {
		g.nextEdge = id + 1
	}
	return e, nil
}

// RemoveEdge removes an edge from the graph and from both ends.
func (g *Graph) RemoveEdge(e *Edge) {
	if e.State == Active {
		e.A.activeEdges--
		e.B.activeEdges--
	}
	e.A.Edges = without(e.A.Edges, e)
	e.B.Edges = without(e.B.Edges, e)
	delete(e.A.neighbor, e.B.ID)
	delete(e.B.neighbor, e.A.ID)
	g.Edges = without(g.Edges, e)
	delete(g.edgeByID, e.ID)
}

// EdgeByID returns the edge with this id, or nil.
func (g *Graph) EdgeByID(id int) *Edge { return g.edgeByID[id] }

// ---------------------------------------------------------------- states

// SetState changes the state of the vertex and notifies the listener.
func (v *Vertex) SetState(s State) {
	v.State = s
	v.graph.notify(Change{VertexKind, v.ID, s})
}

// SetState changes the state of the edge, keeps the active edge count of
// both ends up to date, and notifies the listener.
func (e *Edge) SetState(s State) {
	wasActive, isActive := e.State == Active, s == Active
	switch {
	case isActive && !wasActive:
		e.A.activeEdges++
		e.B.activeEdges++
	case wasActive && !isActive:
		e.A.activeEdges--
		e.B.activeEdges--
	}
	e.State = s
	e.graph.notify(Change{EdgeKind, e.ID, s})
}

// ResetStates puts every element back in None and clears script variables.
func (g *Graph) ResetStates() {
	for _, e := range g.Edges {
		e.SetState(None)
	}
	for _, v := range g.Vertices {
		v.SetState(None)
		v.Vars = map[string]any{}
		v.activeEdges = 0
	}
}

// ShuffleEdges shuffles the edge order of every vertex, which changes the
// traversal order seen by scripts.
func (g *Graph) ShuffleEdges(rng *rand.Rand) {
	for _, v := range g.Vertices {
		rng.Shuffle(len(v.Edges), func(i, j int) { v.Edges[i], v.Edges[j] = v.Edges[j], v.Edges[i] })
	}
}

// ---------------------------------------------------------------- queries

// Adjacent returns the vertex at the other end of e, or nil.
func (v *Vertex) Adjacent(e *Edge) *Vertex {
	if e == nil {
		return nil
	}
	return e.Other(v)
}

// EdgeTo returns the edge connecting v to other, or nil.
func (v *Vertex) EdgeTo(other *Vertex) *Edge { return v.neighbor[other.ID] }

// IsConnected tells whether v and other are neighbours.
func (v *Vertex) IsConnected(other *Vertex) bool {
	_, ok := v.neighbor[other.ID]
	return ok
}

// ActiveEdges returns how many connected edges are Active.
func (v *Vertex) ActiveEdges() int { return v.activeEdges }

// Other returns the end of e that is not v, or nil if v is not an end.
func (e *Edge) Other(v *Vertex) *Vertex {
	switch v {
	case e.A:
		return e.B
	case e.B:
		return e.A
	}
	return nil
}

// ---------------------------------------------------------------- files

// File is the Grafuria JSON format.
type File struct {
	Bidirectional bool         `json:"bidirectional"`
	Vertex        []VertexFile `json:"vertex"`
	Edge          []EdgeFile   `json:"edge"`
}

type VertexFile struct {
	Name string  `json:"name"`
	ID   int     `json:"id"`
	X    float64 `json:"x"`
	Y    float64 `json:"y"`
}

type EdgeFile struct {
	ID     int     `json:"id"`
	A      int     `json:"a"`
	B      int     `json:"b"`
	Weight float64 `json:"weight"`
}

// ToFile returns the graph in the file format. With reindex, ids are
// renumbered 0..n-1 in list order, as Grafuria always saved.
func (g *Graph) ToFile(reindex bool) File {
	f := File{Bidirectional: g.Bidirectional, Vertex: []VertexFile{}, Edge: []EdgeFile{}}
	ids := map[int]int{}
	for i, v := range g.Vertices {
		ids[v.ID] = v.ID
		if reindex {
			ids[v.ID] = i
		}
		f.Vertex = append(f.Vertex, VertexFile{Name: v.Name, ID: ids[v.ID], X: v.X, Y: v.Y})
	}
	for i, e := range g.Edges {
		id := e.ID
		if reindex {
			id = i
		}
		f.Edge = append(f.Edge, EdgeFile{ID: id, A: ids[e.A.ID], B: ids[e.B.ID], Weight: e.Weight})
	}
	return f
}

// FromFile builds a graph from the file format.
func FromFile(f File) (*Graph, error) {
	g := New(f.Bidirectional)
	for _, v := range f.Vertex {
		if _, err := g.AddVertexWithID(v.ID, v.Name, v.X, v.Y); err != nil {
			return nil, err
		}
	}
	for _, e := range f.Edge {
		a, b := g.VertexByID(e.A), g.VertexByID(e.B)
		if a == nil || b == nil {
			return nil, fmt.Errorf("edge %d refers to a missing vertex: %w", e.ID, ErrNotFound)
		}
		if _, err := g.AddEdgeWithID(e.ID, a, b, e.Weight); err != nil {
			return nil, err
		}
	}
	return g, nil
}

// UnmarshalJSON accepts a missing weight as 1, as the original format allows.
func (e *EdgeFile) UnmarshalJSON(data []byte) error {
	type plain EdgeFile
	p := plain{Weight: 1}
	if err := json.Unmarshal(data, &p); err != nil {
		return err
	}
	*e = EdgeFile(p)
	return nil
}

// UnmarshalJSON accepts a missing "bidirectional" as true.
func (f *File) UnmarshalJSON(data []byte) error {
	type plain File
	p := plain{Bidirectional: true}
	if err := json.Unmarshal(data, &p); err != nil {
		return err
	}
	*f = File(p)
	return nil
}

// Load reads a graph file.
func Load(path string) (*Graph, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var f File
	if err := json.Unmarshal(data, &f); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return FromFile(f)
}

// Save writes the graph (ids renumbered), indented so that changes are
// readable in version control.
func (g *Graph) Save(path string) error {
	data, err := json.MarshalIndent(g.ToFile(true), "", "    ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0o644)
}

// without returns s without the first occurrence of x (keeping order).
func without[T comparable](s []T, x T) []T {
	for i, y := range s {
		if y == x {
			return append(s[:i:i], s[i+1:]...)
		}
	}
	return s
}
