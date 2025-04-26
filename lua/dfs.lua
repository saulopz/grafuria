--- Represents a node in a tree structure.
--- 
--- A Node is used to store a reference to a vertex and the edge
--- that connects it to its parent node. This is particularly
--- useful in graph traversal algorithms or tree representations.
---
--- Fields:
--- - `vertex` (Vertex): The vertex associated with this node.
--- - `edge` (Edge): The edge connecting this node to its previous vertex.
---
--- Example usage:
---@class DFSNode
---@field vertex Vertex The vertex represented by this node.
---@field edge Edge Connection to previous vertex in graph.
-- Class Node
DFSNode = {}
DFSNode.__index = DFSNode

--- Constructor method of Node to create a new DFSNode.
---@param vertex Vertex Current vertex.
---@param edge Edge Connection to previous vertex in graph.
function DFSNode.new(vertex, edge)
    local self = setmetatable({}, BFSNode)
    self.vertex = vertex
    self.edge = edge
    return self
end

---@class DFS Depth-First Search Class
---@field origin_pos integer ID of initial vertex in graph
---@field destination_pos integer ID of end vertex in graph
---@field found boolean Flag to inform if we have reached the destination
---@field origin DFSNode initial node with initial vertex
---@field path string Creantes the path with vertex id from origin to destination
DFS = {}
DFS.__index = DFS

--- Constructor method of DFS
---@param origin_pos integer The start vertex point
---@param destination_pos integer The end vertex point
function DFS.new(origin_pos, destination_pos)
    local self = setmetatable({}, DFS)
    self.origin_pos = origin_pos
    self.destination_pos = destination_pos
    self.found = false -- Flag to know if the destination was found
    self.origin = DFSNode.new(app:get_vertex(self.origin_pos), nil)
    self.path = ""
    return self
end

--- Executes the Depth-First Search algorithm
function DFS:run()
    app:log("$Algorithm Depth-First Search (DFS)")
    app:log("$Trying find a way from " .. self.origin_pos .. " to " .. self.destination_pos)
    local start_time = os.clock()
    if self.origin then
        self:visit(self.origin)
    end
    -- Calculate the time it took.
    local end_time = os.clock()
    local elapsed_time = end_time - start_time
    -- Showing the path found.
    app:log("$PATH: [" .. self.path .. " ]")
    app:log("$Algorithm:run Elapsed time: " .. elapsed_time .. " seconds")
end

--- Recursive method thats open a node to continue searching
--- for the path of solution.
---@param current DFSNode Current node to open children.
function DFS:visit(current)
    if not current then
        app:log("$Error: Input node is nil.")
    end
    current.vertex:set_state(State.TESTING)
    app:step()
    if app:is_stopped() then
        return
    end
    local edge_size = current.vertex:get_edge_size()
    for i = 1, edge_size do
        local edge = current.vertex:get_edge(i)
        local vertex_neighbor = current.vertex:get_adjacent(edge)
        if vertex_neighbor and vertex_neighbor:get_state() == State.NONE then
            edge:set_state(State.TESTING)
            vertex_neighbor:set_state(State.TESTING)
            if vertex_neighbor:get_id() == self.destination_pos then
                self.found = true
                app:set_solved(true)
                vertex_neighbor:set_state(State.ACTIVE)
                edge:set_state(State.ACTIVE)
                self.path = " " .. vertex_neighbor:get_id() .. self.path
                break
            end
            local node = DFSNode.new(vertex_neighbor, edge)
            self:visit(node)
            if self.found then
                break
            end
            -- Control commands to synchronize with the application.
            app:step()
            if app:is_stopped() then
                app:set_solved(false)
                return
            end
        end
    end
    app:step()
    if self.found then
        current.vertex:set_state(State.ACTIVE)
        self.path = " " .. current.vertex:get_id() .. self.path
        if current.edge then
            current.edge:set_state(State.ACTIVE)
        end
    end
end

--- Function main
local function main()
    -- Initializes the random number generator seed
    math.randomseed(os.time())
    local vertex_size = app:get_vertex_size()
    local orig = app:get_vertex(math.random(1, vertex_size)):get_id()
    local dest = app:get_vertex(math.random(1, vertex_size)):get_id()
    DFS.new(orig, dest):run()
end

main()
