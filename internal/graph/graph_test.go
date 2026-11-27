package graph

import (
	"encoding/json"
	"errors"
	"math/rand"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func triangle(t *testing.T) *Graph {
	t.Helper()
	g := New(true)
	a, b, c := g.AddVertex("a", 0, 0), g.AddVertex("b", 1, 0), g.AddVertex("c", 0, 1)
	for _, pair := range [][2]*Vertex{{a, b}, {b, c}, {c, a}} {
		if _, err := g.AddEdge(pair[0], pair[1], 1); err != nil {
			t.Fatal(err)
		}
	}
	return g
}

func TestAddAndAdjacency(t *testing.T) {
	g := triangle(t)
	a, b, c := g.Vertices[0], g.Vertices[1], g.Vertices[2]
	if len(g.Vertices) != 3 || len(g.Edges) != 3 {
		t.Fatalf("got %d vertices, %d edges", len(g.Vertices), len(g.Edges))
	}
	if !a.IsConnected(b) || !b.IsConnected(a) {
		t.Fatal("a and b must be connected both ways")
	}
	ab := a.EdgeTo(b)
	if ab != b.EdgeTo(a) || a.Adjacent(ab) != b || ab.Other(b) != a || ab.Other(c) != nil {
		t.Fatal("adjacency is inconsistent")
	}
}

func TestIDsArePerGraph(t *testing.T) {
	g1, g2 := triangle(t), triangle(t)
	for _, g := range []*Graph{g1, g2} {
		for i, v := range g.Vertices {
			if v.ID != i {
				t.Fatalf("vertex %d has id %d", i, v.ID)
			}
		}
	}
	g3 := New(true)
	if _, err := g3.AddVertexWithID(10, "", 0, 0); err != nil {
		t.Fatal(err)
	}
	if id := g3.AddVertex("", 0, 0).ID; id != 11 {
		t.Fatalf("next id = %d, want 11", id)
	}
}

func TestRejectsDuplicatesAndLoops(t *testing.T) {
	g := triangle(t)
	a, b := g.Vertices[0], g.Vertices[1]
	if _, err := g.AddEdge(a, b, 1); !errors.Is(err, ErrConnected) {
		t.Errorf("duplicate edge: %v", err)
	}
	if _, err := g.AddEdge(a, a, 1); !errors.Is(err, ErrLoop) {
		t.Errorf("loop: %v", err)
	}
	if _, err := g.AddVertexWithID(0, "", 0, 0); !errors.Is(err, ErrDuplicateID) {
		t.Errorf("duplicate vertex id: %v", err)
	}
}

func TestActiveEdgeCounter(t *testing.T) {
	g := triangle(t)
	a, b, c := g.Vertices[0], g.Vertices[1], g.Vertices[2]
	ab, bc := a.EdgeTo(b), b.EdgeTo(c)
	ab.SetState(Active)
	ab.SetState(Active) // setting twice must not count twice
	bc.SetState(Active)
	if a.ActiveEdges() != 1 || b.ActiveEdges() != 2 {
		t.Fatalf("got %d, %d", a.ActiveEdges(), b.ActiveEdges())
	}
	ab.SetState(Testing)
	if a.ActiveEdges() != 0 || b.ActiveEdges() != 1 {
		t.Fatalf("after Testing: %d, %d", a.ActiveEdges(), b.ActiveEdges())
	}
	g.RemoveEdge(bc)
	if c.ActiveEdges() != 0 {
		t.Fatal("removing an active edge must update the counter")
	}
}

func TestRemoveVertexRemovesItsEdges(t *testing.T) {
	g := triangle(t)
	a, b := g.Vertices[0], g.Vertices[1]
	g.RemoveVertex(a)
	if len(g.Edges) != 1 || b.IsConnected(a) || g.VertexByID(a.ID) != nil || len(b.Edges) != 1 {
		t.Fatal("vertex removal left edges behind")
	}
}

func TestResetStates(t *testing.T) {
	g := triangle(t)
	for _, e := range g.Edges {
		e.SetState(Active)
	}
	g.Vertices[0].Vars["visited"] = true
	g.ResetStates()
	for _, e := range g.Edges {
		if e.State != None {
			t.Fatal("edge not reset")
		}
	}
	for _, v := range g.Vertices {
		if v.ActiveEdges() != 0 || len(v.Vars) != 0 {
			t.Fatal("vertex not reset")
		}
	}
}

func TestListenerReceivesTheNewState(t *testing.T) {
	g := triangle(t)
	var seen []Change
	g.Listener = func(c Change) { seen = append(seen, c) }
	g.Vertices[0].SetState(Testing)
	g.Edges[1].SetState(Active)
	want := []Change{{VertexKind, g.Vertices[0].ID, Testing}, {EdgeKind, g.Edges[1].ID, Active}}
	if !reflect.DeepEqual(seen, want) {
		t.Fatalf("got %+v, want %+v", seen, want)
	}
}

func TestShuffleIsReproducible(t *testing.T) {
	order := func(seed int64) []int {
		g, err := Load(filepath.Join("..", "..", "graphs", "big_circle.json"))
		if err != nil {
			t.Fatal(err)
		}
		g.ShuffleEdges(rand.New(rand.NewSource(seed)))
		var ids []int
		for _, e := range g.Vertices[0].Edges {
			ids = append(ids, e.ID)
		}
		return ids
	}
	if !reflect.DeepEqual(order(7), order(7)) {
		t.Fatal("same seed must give the same order")
	}
	if reflect.DeepEqual(order(7), order(8)) {
		t.Fatal("different seeds should give different orders")
	}
}

func TestToFileReindexes(t *testing.T) {
	g := New(true)
	a, _ := g.AddVertexWithID(5, "a", 0, 0)
	b, _ := g.AddVertexWithID(9, "b", 0, 0)
	if _, err := g.AddEdgeWithID(7, a, b, 2.5); err != nil {
		t.Fatal(err)
	}
	f := g.ToFile(true)
	if f.Vertex[0].ID != 0 || f.Vertex[1].ID != 1 {
		t.Fatalf("vertex ids %+v", f.Vertex)
	}
	if want := (EdgeFile{ID: 0, A: 0, B: 1, Weight: 2.5}); f.Edge[0] != want {
		t.Fatalf("edge %+v, want %+v", f.Edge[0], want)
	}
	if kept := g.ToFile(false); kept.Vertex[1].ID != 9 || kept.Edge[0].A != 5 {
		t.Fatal("without reindex the ids must be kept")
	}
}

func TestMissingFieldsTakeDefaults(t *testing.T) {
	var f File
	if err := json.Unmarshal([]byte(`{"vertex":[{"id":0,"x":0,"y":0},{"id":1,"x":0,"y":0}],"edge":[{"id":0,"a":0,"b":1}]}`), &f); err != nil {
		t.Fatal(err)
	}
	if !f.Bidirectional || f.Edge[0].Weight != 1 {
		t.Fatalf("defaults not applied: %+v", f)
	}
}

func TestAllBundledGraphsLoadAndRoundTrip(t *testing.T) {
	files, _ := filepath.Glob(filepath.Join("..", "..", "graphs", "*.json"))
	if len(files) == 0 {
		t.Fatal("no graphs found")
	}
	dir := t.TempDir()
	for _, path := range files {
		t.Run(filepath.Base(path), func(t *testing.T) {
			raw, _ := os.ReadFile(path)
			var original File
			if err := json.Unmarshal(raw, &original); err != nil {
				t.Fatal(err)
			}
			g, err := Load(path)
			if err != nil {
				t.Fatal(err)
			}
			if len(g.Vertices) != len(original.Vertex) || len(g.Edges) != len(original.Edge) {
				t.Fatal("counts differ from the file")
			}
			out := filepath.Join(dir, filepath.Base(path))
			if err := g.Save(out); err != nil {
				t.Fatal(err)
			}
			g2, err := Load(out)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(g.ToFile(true), g2.ToFile(true)) {
				t.Fatal("save and load changed the graph")
			}
		})
	}
}

func TestSaveIsIndented(t *testing.T) {
	path := filepath.Join(t.TempDir(), "t.json")
	if err := triangle(t).Save(path); err != nil {
		t.Fatal(err)
	}
	data, _ := os.ReadFile(path)
	if lines := strings.Count(string(data), "\n"); lines < 20 {
		t.Fatalf("saved file has %d lines; it must be indented", lines)
	}
}
