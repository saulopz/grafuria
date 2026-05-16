dofile("scripts/nemertea/node.lua")

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
---@class NBFS Nemertea's Breadth First Search.
---@field root Node Root node to starts NBFS.
---@field level number Current node of leaves.
---@field leaves Node[] List of leaves nodes.
---@field found boolean Identify if we have reached the destination.
---@field node Node Destination node found for new path.
---@field new_vertices number Number of new vertices added to PATH.
NBFS = {}
NBFS.__index = NBFS

-- =========================
-- Constructor
-- =========================
--- Constructor do Best First Search customized.
---@param vertex Vertex Root vertex.
---@return NBFS Returns the instantiation of the NBFS class object.
function NBFS.new(vertex, first)
    local self = setmetatable({}, NBFS)
    self.root = Node.new(vertex)
    self.first = first
    self.level = 1
    self.leaves = {self.root}
    self.found = false
    self.node = nil
    self.new_vertices = 0
    return self
end

-- =========================
-- Run
-- =========================
--- Executes the custom Breadth-First Search algorithm. For each level, not
--- every vertex can be used as a child. These rules are described in the
--- @get_child() method.
function NBFS:run()
    local r = self.root
    local first = self.first
    while #self.leaves > 0 and not self.found and self.level <= app:get_var("deep") do
        local new_level = {} -- Open leaves of this level to create a new level
        for i = 1, #self.leaves do -- For each leaf of this level
            app:step()
            local n = self.leaves[i]
            local edge_size = n.vertex:get_edge_size()
            for j = 1, edge_size do -- For each vertex's edge of this leaf
                app:step()
                local e = n.vertex:get_edge(j) -- Get the edge
                local child
                child, self.found = self:select_child(r, n, e, first) -- get child if valid
                if self.found then -- If get_child returns true, than a vertex target was found
                    self.node = child
                    break
                elseif child then -- If it's a valid child, but not found target, add child to new_level
                    table.insert(new_level, child)
                end
            end
            if app:is_stopped() then -- Finish algorithm if user calls stop command
                return
            end
            if self.found then -- If found, get out of this algorithm
                break
            end
        end
        if not self.found then -- if not found, leaves of level is now new_level
            self.level = self.level + 1
            self.leaves = new_level
        end
        if app:is_stopped() then
            return self.new_vertices
        end
    end
    if self.found then
        self:make_path(self.node) -- Make the demarcation of new path, and unmark the old
    end
    self:destroy(self.root) -- Destroy the tree
    return self.new_vertices -- Returns how much vertex was added to path
end

-- =========================
-- Get Child
-- =========================
--- Get a valid child of parent node vertex and it's edge
---@param node Node to verify (Node)
---@param edge Edge connected to parent to verify (Edge)
---@return Node returns a child if valid or found, and nil if not valid (Node)
---@return boolean true if found a target or false if not found (boolean)
function NBFS:select_child(root, node, edge, first)

    -- Case 1: If I'm trying to follow an edge that's already in the path.
    --         It can happen in the first iteration.
    if edge:get_state() == State.ACTIVE then
        return nil, false
    end

    local adjacent = node.vertex:get_adjacent(edge) -- adjacent vertex

   
    if adjacent:get_state() == State.TESTING then
        -- Case 2: General blocking of TESTING outside of the first iteration.
        if not first then
            return nil, false
        end
        -- Case 3: Ancestor locking in the tree during the first iteration.
        local ancestor = node.parent
        while ancestor do
            if ancestor.vertex:get_id() == adjacent:get_id() then
                return nil, false  -- é ancestral — ignora
            end
            ancestor = ancestor.parent
        end
        -- não é ancestral — pode continuar (será avaliado pelos casos seguintes)
    end

    -- Case 4: If adjacent is my parent, then I'm going back to parent. Not valid.
    if node.parent and adjacent:get_id() == node.parent.vertex:get_id() then
        return nil, false
    end

    -- Case 5: If it is the source node and does not yet have active connections,
    --         then it is the first conquered area.
    if adjacent:get_id() == root.vertex:get_id() and root.vertex:get_active_edge_size() == 0 then
        return node:add_child(adjacent), true
    end

    if adjacent:get_state() == State.ACTIVE then
        
        -- Case 6: vertex is active and it's a root neighbor, than i found target
        local edge = adjacent:get_edge_to(root.vertex)
        if edge and edge:get_state() == State.ACTIVE then
            return node:add_child(adjacent), true
        end

        -- Case 7: The adjacent vertex is ACTIVE. It's alread in frontier and it's not valid.
        return nil, false
    end

    -- Case 8: free vertex, so I add it as a child node.
    edge:set_state(State.TESTING)
    adjacent:set_state(State.TESTING)
    return node:add_child(adjacent), false
end

-- =========================
-- Make Path
-- =========================
--- After finding a neighboring active node, this method
--- breaks this connection with its neighbor and connects
--- the found path by creating a new PATH from the start
--- vertex to the end vertex of this iteration.
---@param node Node Represent the vertex neighbor of root.
function NBFS:make_path(node)

    -- If there is an active connection to the root node,
    -- I disconnect it because now we have a new path to
    -- be added to the PATH.
    if node.vertex:get_state() == State.ACTIVE then
        local edge = self.root.vertex:get_edge_to(node.vertex)
        if edge and edge:get_state() == State.ACTIVE then
            edge:set_state(State.NONE)
        end
    end

    -- Mark the vertices and nodes as active until reaching the
    -- starting vertex.
    local n = node
    while n.parent do
        -- If vertex is not active, a new vertex was added.
        if n.vertex:get_state() ~= State.ACTIVE then
            self.new_vertices = self.new_vertices + 1
        end
        n.vertex:set_state(State.ACTIVE)
        n.edge:set_state(State.ACTIVE)
        n = n.parent
    end
end

-- =========================
-- Destroy
-- =========================
--- Recursive function to destroy nodes of NBFS tree
---@param node Node A node element to destroy it's subtree.
function NBFS:destroy(node)
    for i = 1, #node.children do
        local child = node.children[i]
        if child then
            self:destroy(child)
            child:destroy()
        end
    end
    node.children = nil
end
