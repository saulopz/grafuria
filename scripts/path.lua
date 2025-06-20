path = {}
end_vertex = nil
found = false

function first_path(root)
    root:set_state(State.ACTIVE)
    table.insert(path, root:get_id())
    local edge_size = root:get_edge_size()
    for i = 1, edge_size do
        local edge = root:get_edge(i)
        if edge:get_state() ~= State.ACTIVE then
            local adjacent = root:get_adjacent(edge)
            if adjacent:get_state() ~= State.ACTIVE then
                edge:set_state(State.ACTIVE)
                if end_vertex and adjacent:get_id() == end_vertex then
                    found = true
                    return 0
                end
                app:step()
                return first_path(adjacent) + 1
            end
        end
    end
    return 0
end

function main()
    local vertex_size = app:get_vertex_size()
    local begin = nil
    if app:get_var("begin") == -1 then
        math.randomseed(os.time())
        begin = app:get_vertex(math.random(1, vertex_size))
    else
        begin = app:get_vertex(app:get_var("begin"))
    end
    if app:get_var("end") > -1 then
        end_vertex = app:get_var("end")
    end
    local path_size = first_path(begin) + 1
    local path_str = table.concat(path, ", ")
    app:log("#Path: " .. path_str)
    app:log("#Vertex on path: " .. path_size .. " of " .. vertex_size)
    app:set_solved(true)
end

main()
