dofile("scripts/nemertea/nbfs.lua")

--- Nemertea Algorithm
---@author Saulo Popov Zambiasi
---@language Lua
---@version 1.2
---@since 10/10/2021
---@update 08/05/2025
---@description
---
--- Nemertea is an algorithm for solving the Hamiltonian cycle
--- problem in graphs. It is a heuristic algorithm that
--- uses territorial conquest as a strategy. The algorithm
--- starts in a random closed region and adds new closed regions
--- until all vertices are part of the boundaries of that
--- territory. To add new regions, a vertex v is taken from the
--- frontier and follows paths and external vertices of the
--- frontier until it finds a vertex u that is a neighbor of v
--- and is on the frontier, with no other vertices between them.
--- The path taken from v to u through the external area is
--- added as a new frontier and the boundary that was between v
--- and u is undone. In this way, a new area is added to the
--- territory. To find this new region, the algorithm uses a
--- custom Breadth First Search.
---
--- This lua code is executed in the Grafuria software for
--- creating and editing graphs and executing algorithms on
--- the graphs:
---
--- https://github.com/saulopz/grafuria
---

--- Executes the Nemertea algorithm.
--- @return number Returns the number of vertices in the path.
function nemertea()
    app:log("#Nemertea starting...")
    local prev = nil -- Vertex before the current one
    local path_size = 1 -- Number of vertices in the path
    local vertex_size = app:get_vertex_size() -- Number of vertices in the graph
    -- Randomly selects a vertex to start the algorithm
    local first_vertex = app:get_vertex(math.random(1, vertex_size))
    local current = first_vertex -- Starting current vertex at the first
    local start_time = os.clock()
    current:set_state(State.ACTIVE) -- Sets the current status to active
    local first = true

    -- If is a Hamiltonian Path, we create first path from the
    -- initial vertex until not find a valid way. If it is a
    -- Hamiltonian Cycle, we do not execute this
    if not app:get_var("cycle") then
        -- Adds the first path to the current vertex
        path_size = path_size + first_path(first_vertex)
        first = false
    end

    repeat -- Scans active vertices to conquer new regions    
        -- Run NBFS to expand the PATH until no new vertices are added
        repeat
            -- Run NBFS to expand the PATH until no new vertices are added
            local size = NBFS.new(current, first):run()
            path_size = path_size + size

            -- If command stops, exit the algorithm
            if app:is_stopped() then
                return 0
            end
            first = false
        until size == 0 -- NBFS not create a new path

        -- Go to the next vertex without returning to prev.
        local next = next_vertex(prev, current)
        prev = current
        current = next

        -- If command stops, exit the script
        if app:is_stopped() then
            return 0
        end

        -- It returned to the initial vertex or the path
        -- size is equal to the number of vertices in the graph.
    until not current or current:get_id() == first_vertex:get_id() or path_size == vertex_size
    local end_time = os.clock()
    local execution_time = end_time - start_time
    app:set_execution_time(execution_time)
    app:log("#Execution time: " .. execution_time .. " seconds")
    return path_size
end

--- Returns the next vertex in the graph that is on the frontier.
--- prev is passed as a parameter so that the algorithm does not
--- follow where it came from, which can cause an unwanted loop.
---@param prev Vertex previous vertex
---@param current Vertex current vertex
---@return Vertex Returns the next vertex in the path.
function next_vertex(prev, current)
    local edge_size = current:get_edge_size()
    for i = 1, edge_size do
        local e = current:get_edge(i)

        -- If edge is Active, then it's in PATH
        if e:get_state() == State.ACTIVE then
            local adjacent = current:get_adjacent(e)

            -- If prev is nil, then we are in the first iteration or
            -- if the adjacent vertex is not equal to the previous one,
            -- then we can return it.
            if prev == nil or adjacent:get_id() ~= prev:get_id() then
                return adjacent
            end
        end
    end
    return nil
end

--- First path of the graph.
--- This function is used to find the first path of the graph
--- in case of Hamiltonian path. Hamiltonian cycle not use this
--- @param root Vertex root vertex
--- @return number Returns the number of vertices in the path.
function first_path(root)
    local size = 0
    local p = root
    repeat
        app:step()
        local found = false
        local edge_size = p:get_edge_size()
        local i = 1
        while (i <= edge_size and not found) do
            local edge = p:get_edge(i)
            if edge:get_state() ~= State.ACTIVE then
                local adjacent = p:get_adjacent(edge)
                if adjacent:get_state() ~= State.ACTIVE then
                    edge.set_state(State.ACTIVE)
                    adjacent.set_state(State.ACTIVE)
                    p = adjacent
                    found = true
                    size = size + 1
                end
            end
            i = i + 1
        end
    until found == false
    return size
end

--- Evaluates whether the algorithm was successful.
--- If the algorithm reaches all vertices, it has
--- found a Hamiltonian cycle in the graph. Otherwise,
--- it is undefined.
--- @param path_size number Number of vertices in the path
function evaluate(path_size)
    local vertex_size = app:get_vertex_size()
    local remaining_vertices = vertex_size - path_size
    if vertex_size == path_size then
        app:set_solved(true)
        app:log("#The algorithm nemertea solves the Hamiltonian path problem for this graph.")
    else
        app:set_solved(false)
        app:log("#The algorithm nemertea not to solve the Hamiltonian path problem for this graph.")
        app:log("#Vertex on path: " .. path_size .. " of " .. vertex_size .. ", " .. remaining_vertices .. " left.")
    end
end

-- =========================
-- Nemertea initialization
-- =========================

-- Initializes the random number generator seed
math.randomseed(os.time())
path_size = nemertea()
evaluate(path_size)
