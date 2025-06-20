class ScriptType:
    """
    Enumeration to represent the type of script.

    Attributes
    ----------
    NONE : int
        Represents no script.
    PYTHON : int
        Represents a Python script.
    LUA : int
        Represents a Lua script.
    """

    NONE = 0
    PYTHON = 1
    LUA = 2

class State:
    """
    Enumeration to represents Edge, Vertex and Node states.

    Attributes
    ----------
    NONE : int
        Represents an element without state.
    TESTING : int
        Represents an element that is being tested.
    ACTIVE : int
        Represents an element activated.
    INVALID : int
        Represents an invalid element.
    """

    NONE = 0
    TESTING = 1
    ACTIVE = 2
    INVALID = 3
