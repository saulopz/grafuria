-- Greedy walk (Grafuria tutorial)
--
-- Starts at a vertex and keeps moving to a neighbour that was not
-- visited yet. Stops when the current vertex has no such neighbour.
-- If it visits every vertex, it found a Hamiltonian path.

-- Parameter "start" (walk.json): a vertex id, or -1 for a random vertex.
local start
if app:get_var("start") == -1 then
    start = app:get_vertex(math.random(1, app:get_vertex_size())) -- Lua: 1..n
else
    start = app:get_vertex_by_id(app:get_var("start"))
end
if not start then
    app:log("#Start vertex not found: check the 'start' parameter.")
    return
end

local current = start
current:set_state(State.ACTIVE)
local visited = 1
app:log("#Starting at vertex " .. current:get_id())

while not app:is_stopped() do
    local next_vertex, next_edge = nil, nil

    -- Look at the edges of the current vertex (Lua counts from 1).
    for i = 1, current:get_edge_size() do
        local edge = current:get_edge(i)
        local neighbour = current:get_adjacent(edge)
        if neighbour:get_state() == State.NONE then
            neighbour:set_state(State.TESTING) -- show the candidate
            app:step()                         -- pause, as the speed says
            next_vertex, next_edge = neighbour, edge
            break
        end
    end

    if not next_vertex then
        break -- stuck: every neighbour was visited
    end

    next_edge:set_state(State.ACTIVE)
    next_vertex:set_state(State.ACTIVE)
    current = next_vertex
    visited = visited + 1
    app:log("$Moved to vertex " .. current:get_id())
end

local total = app:get_vertex_size()
app:log("#Visited " .. visited .. " of " .. total .. " vertices.")
app:set_solved(visited == total)
