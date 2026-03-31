# retrieval_architecture/handlers_structure.py

from architecture import load_architecture_graph


_graph_cache = None

def get_graph():
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = load_architecture_graph()
    return _graph_cache


def find_importers(target_module: str):
    graph = get_graph()
    return [
        mod for mod, deps in graph.items()
        if target_module in deps.imports
    ]


def find_callers(function_name: str):
    graph = get_graph()
    return [
        mod for mod, deps in graph.items()
        if function_name in deps.calls
    ]


def list_classes(module: str):
    graph = get_graph()
    if module in graph:
        return sorted(graph[module].classes)
    return []


def list_functions(module: str):
    graph = get_graph()
    if module in graph:
        return sorted(graph[module].functions)
    return []


def module_dependencies(module: str):
    graph = get_graph()
    if module not in graph:
        return {}
    deps = graph[module]
    return {
        "imports": sorted(deps.imports),
        "classes": sorted(deps.classes),
        "functions": sorted(deps.functions),
        "calls": sorted(deps.calls),
    }


def handle_structure_query(query: str):
    q = query.lower()

    if q.startswith("who imports "):
        mod = q.replace("who imports ", "").strip()
        return {"importers": find_importers(mod)}

    if q.startswith("who calls "):
        fn = q.replace("who calls ", "").strip()
        return {"callers": find_callers(fn)}

    if q.startswith("list classes in "):
        mod = q.replace("list classes in ", "").strip()
        return {"classes": list_classes(mod)}

    if q.startswith("list functions in "):
        mod = q.replace("list functions in ", "").strip()
        return {"functions": list_functions(mod)}

    if q.startswith("show dependencies for "):
        mod = q.replace("show dependencies for ", "").strip()
        return module_dependencies(mod)

    return {"error": "Unrecognized architecture query"}
