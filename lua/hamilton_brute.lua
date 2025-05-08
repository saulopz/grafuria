--- Verifica se o caminho atual forma um ciclo hamiltoniano
---@param path table Caminho atual (lista de vértices)
---@return boolean Retorna true se o caminho for um ciclo hamiltoniano
local function is_hamiltonian_cycle(path)
    local n = app:get_vertex_size()
    local visited = {}

    -- Verifica se todos os vértices foram visitados
    for _, vertex in ipairs(path) do
        if visited[vertex:get_id()] then
            return false -- Vértice já visitado
        end
        visited[vertex:get_id()] = true
    end

    -- Verifica se o último vértice está conectado ao primeiro
    local last = path[#path]
    local first = path[1]
    for i = 1, last:get_edge_size() do
        local edge = last:get_edge(i)
        local neighbor = last:get_adjacent(edge)
        if neighbor:get_id() == first:get_id() then
            return #path == n
        end
    end

    return false
end

--- Gera todas as permutações dos vértices e verifica se há um ciclo hamiltoniano
---@param path table Caminho atual (lista de vértices)
---@return table|nil Retorna o ciclo hamiltoniano encontrado ou nil se não houver
local function find_hamiltonian_cycle(path)
    local n = app:get_vertex_size()

    -- Verifica se o caminho atual é um ciclo hamiltoniano
    if #path == n then
        if is_hamiltonian_cycle(path) then
            return path
        end
        return nil
    end

    -- Itera sobre todos os vértices
    for i = 1, n do
        local vertex = app:get_vertex(i)
        local already_in_path = false

        -- Verifica se o vértice já está no caminho
        for _, v in ipairs(path) do
            if v:get_id() == vertex:get_id() then
                already_in_path = true
                break
            end
        end

        if not already_in_path then
            local new_path = {unpack(path)}
            table.insert(new_path, vertex)

            -- Verifica se o usuário interrompeu a execução
            if app:is_stopped() then
                return nil
            end

            local result = find_hamiltonian_cycle(new_path)
            if result then
                return result
            end
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
    local cycle = find_hamiltonian_cycle({})
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
    else
        app:log("#Nenhum ciclo Hamiltoniano encontrado.")
    end
end

brute_force_hamiltonian()
