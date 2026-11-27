--- Verifica se dois vértices são adjacentes
---@return boolean
local function is_adjacent(a, b)
    return a:is_connected(b)
end

--- Busca em profundidade com retrocesso (backtracking).
--- Só estende o caminho por vizinhos do último vértice, então todo
--- par consecutivo do caminho é uma aresta do grafo. O primeiro
--- vértice é fixo: um ciclo é o mesmo em qualquer rotação.
---@param path table Caminho atual (lista de vértices)
---@param in_path table Conjunto de ids já no caminho
---@param n number Número de vértices do grafo
---@return table|nil Ciclo hamiltoniano encontrado ou nil
local function find_hamiltonian_cycle(path, in_path, n)
    if app:is_stopped() then
        return nil
    end

    local last = path[#path]
    if #path == n then
        -- Fecha o ciclo: o último precisa ser vizinho do primeiro
        if is_adjacent(last, path[1]) then
            return path
        end
        return nil
    end

    for i = 1, last:get_edge_size() do
        local edge = last:get_edge(i)
        local neighbor = last:get_adjacent(edge)
        if not in_path[neighbor:get_id()] then
            table.insert(path, neighbor)
            in_path[neighbor:get_id()] = true
            if find_hamiltonian_cycle(path, in_path, n) then
                return path
            end
            in_path[neighbor:get_id()] = nil
            table.remove(path)
        end
    end

    return nil
end

--- Executa o algoritmo de força bruta para encontrar um ciclo hamiltoniano
function brute_force_hamiltonian()
    app:log("#Iniciando busca de ciclo hamiltoniano (força bruta)...")
    local start_time = os.clock()
    local vertices = {}
    local n = app:get_vertex_size()

    -- Obtém todos os vértices do grafo
    for i = 1, n do
        table.insert(vertices, app:get_vertex(i))
    end

    -- Inicia a busca
    local cycle = nil
    if n > 0 then
        local first = app:get_vertex(1)
        cycle = find_hamiltonian_cycle({ first }, { [first:get_id()] = true }, n)
    end
    if cycle then
        app:log("#Ciclo Hamiltoniano encontrado:")
        for _, vertex in ipairs(cycle) do
            app:log("Vértice: " .. vertex:get_id())
        end

        -- Marcar os vértices e arestas do ciclo como ativos
        for i = 1, #cycle do
            local current = cycle[i]
            local next = cycle[i % #cycle + 1] -- Próximo vértice (circular)

            -- Marcar o vértice como ativo
            current:set_state(State.ACTIVE)

            -- Encontrar e marcar a aresta entre o vértice atual e o próximo
            local edge_size = current:get_edge_size()
            for j = 1, edge_size do
                local edge = current:get_edge(j)
                local neighbor = current:get_adjacent(edge)
                if neighbor:get_id() == next:get_id() then
                    edge:set_state(State.ACTIVE)
                    break
                end
            end
        end
        local end_time = os.clock()
        local execution_time = end_time - start_time
        app:set_execution_time(execution_time)
        app:log("#Execution time: " .. execution_time .. " seconds")
        app:set_solved(true)
    else
        app:log("#Nenhum ciclo Hamiltoniano encontrado.")
        app:set_solved(false)
    end
end

brute_force_hamiltonian()
