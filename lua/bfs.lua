--- Represents a node in a tree structure.
--- 
--- A Node is used to store a reference to a vertex and the edge
--- that connects it to its parent node. This is particularly
--- useful in graph traversal algorithms or tree representations.
---
--- Fields:
--- - `vertex` (Vertex): The vertex associated with this node.
--- - `edge` (Edge): The edge connecting this node to its parent.
--- - `parent` (Node): The parent node in the tree.
---
--- Example usage:
---@class BFSNode
---@field vertex Vertex The vertex represented by this node.
---@field edge Edge Connection to the parent
---@field parent BFSNode Parent node
BFSNode = {}
BFSNode.__index = BFSNode

--- Constructor method of Node to create a new BFSNode.
---@param vertex Vertex
---@param edge Edge
---@param parent BFSNode
function BFSNode.new(vertex, edge, parent)
    local self = setmetatable({}, BFSNode)
    self.vertex = vertex
    self.edge = edge
    self.parent = parent
    return self
end

---@class BFS Breadth First Search Class
---@field origin_pos integer ID of initial vertex in graph
---@field destination_pos integer ID of end vertex in graph
---@field queue table List of leaves of current level
---@field visited table List of visited nodes
---@field found boolean Flag to inform if we have reached the destination
---@field origin BFSNode initial node with initial vertex
---@field destination BFSNode
BFS = {}
BFS.__index = BFS

--- Constructor method of BFS
---@param origin_pos integer The start vertex point
---@param destination_pos integer The end vertex point
function BFS.new(origin_pos, destination_pos)
    local self = setmetatable({}, BFS)
    self.origin_pos = origin_pos
    self.destination_pos = destination_pos
    self.queue = {}
    self.visited = {}
    self.found = false
    self.origin = BFSNode.new(app:get_vertex(self.origin_pos), nil, nil)
    self.destination = nil
    table.insert(self.queue, self.origin) -- Add the origin node to the queue
    return self
end

--- Executes the Breadth First Search algorithm
function BFS:run()
    app:log("$Algorithm Breadth First Search (BFS)")
    app:log("$Trying find a way from " .. self.origin_pos .. " to " .. self.destination_pos)
    local start_time = os.clock()
    while #self.queue > 0 and not self.found do
        local current = table.remove(self.queue, 1)
        -- set as visited
        table.insert(self.visited, current)
        current.vertex:set_state(State.TESTING)
        if current.edge then
            current.edge:set_state(State.TESTING)
        end

        if current.vertex:get_id() == self.destination_pos then
            self.found = true
            app:log("$Destination found!")
            app:set_solved(true)
            self.destination = current
            break -- We get out of the loop if we find destiny
        end

        local edge_size = current.vertex:get_edge_size()
        for i = 1, edge_size do
            local edge = current.vertex:get_edge(i)
            local neighbor = current.vertex:get_adjacent(edge)
            if neighbor:get_state() ~= State.TESTING then
                local node = BFSNode.new(neighbor, edge, current)
                table.insert(self.queue, node)
            end
        end
        -- Control commands to synchronize with the application.
        app:step()
        if app:is_stopped() then
            app:set_solved(false)
            return
        end
    end
    if not self.found then
        app:log("$Destination not found.")
        app:set_solved(false)
        return
    end
    -- Calculate the time it took.
    local end_time = os.clock()
    local elapsed_time = end_time - start_time
    
    -- Mark the path back from origin to destination
    self:mark_path_as_active()
    app:log("$Algorithm:run Elapsed time: " .. elapsed_time .. " seconds")
end

--- Marc the path of origin vertex to destination vertex as ACTIVE
function BFS:mark_path_as_active()
    local path = ""
    local current = self.destination
    repeat
        -- Add current vertex ID to path
        path = current.vertex:get_id() .. " " .. path

        -- Mark current vertex and edge to it's parent as ACTIVE
        -- if current is not then origin vertex
        current.vertex:set_state(State.ACTIVE)
        if current.edge then
            current.edge:set_state(State.ACTIVE)
        end

        -- Move current to parent vertex
        current = current.parent
    until current == nil
    app:log("$path [ " .. path .. "]")
end

--- Function main
--- Run the BFS algorithm with a random origin and random destination.
local function main()
    local vertex_size = app:get_vertex_size()
    -- Get random origin and destination vertex from graph
    local orig = app:get_vertex(math.random(1, vertex_size)):get_id()
    local dest = app:get_vertex(math.random(1, vertex_size)):get_id()
    BFS.new(orig, dest):run()
end

main()
