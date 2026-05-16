--- 
--- A Node is used to store a reference to a vertex, the edge
--- that connects it to its parent node and a list of edges that
--- connects to other vertices. This is particularly useful in
--- graph traversal algorithms or tree representations.
---
--- Fields:
--- - `vertex` (Vertex): The vertex associated with this node.
--- - `parent` (Node): The parent node in the tree.
--- - `edge` (Edge): The edge connecting this node to its parent.
--- - `children` (Edge[]): List of edges to connect it's children
---
---@class Node
---@field vertex Vertex The vertex represented by this node.
---@field parent Node Parent node
---@field edge Edge Connection to the parent
---@field children Edge[] List of edges that connects with other vertices
Node = {}
Node.__index = Node

-- =========================
-- Constructor
-- =========================
--- Constructor of Node object
---@param vertex Vertex Each node represents a vertex on graph.
---@return Node
function Node.new(vertex)
    local self = setmetatable({}, Node)
    self.vertex = vertex -- Each node has a vertex on graph
    self.parent = nil -- Node parent
    self.edge = nil -- Edge that connects vertex of node parent
    self.children = {} -- List of edges to connect it's children
    return self
end

-- =========================
-- Add Child
-- =========================
--- Create a new node child. Each node can have many children.
---@param vertex Vertex
---@return Node Returns a node to represents this vertex.
function Node:add_child(vertex)
    local child = Node.new(vertex)
    child.parent = self -- The vertex is a child of this node.
    child.edge = self.vertex:get_edge_to(vertex) -- Edge to parent
    table.insert(self.children, child)
    return child
end

-- =========================
-- Destroy
-- =========================
--- Destroy it's node and set state of it's vertex to NONE
function Node:destroy()
    if self.parent and self.edge:get_state() ~= State.ACTIVE then
        self.edge:set_state(State.NONE)
    end
    if self.vertex:get_state() ~= State.ACTIVE then
        self.vertex:set_state(State.NONE)
    end
    self.parent = nil
    self.children = nil
end