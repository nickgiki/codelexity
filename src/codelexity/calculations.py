import ast
import dis
import importlib.machinery
import re
import sys
import sysconfig
from math import log, sin, sqrt
from pathlib import Path

from codelexity.halstead import halstead_metrics

MULTILINE_COMMENTS = re.compile(r"^[\t ]*\"\"\".*?\"\"\"|^[\t ]*'''.*?'''", re.DOTALL | re.MULTILINE)
SINGLE_LINE_COMMENTS = re.compile(r"^[ \t]*#", re.MULTILINE)
EMPTY_LINES = re.compile("^[ \t]*$", re.MULTILINE)

# One decision point each. BoolOp is counted separately: `a and b and c` is two branches, not one.
DECISION_POINTS = (
    ast.If,
    ast.IfExp,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.Assert,
    ast.match_case,
)


def empty_lines(string: str):
    return re.findall(EMPTY_LINES, string)


def comments_and_docstrings(string: str):
    return re.findall(SINGLE_LINE_COMMENTS, string) + re.findall(MULTILINE_COMMENTS, string)


def functions(string):
    tree = ast.parse(string)
    fns = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fns.append(ast.get_source_segment(string, node))
    return fns


def cyclomatic_complexity(module_source: str):
    """McCabe complexity for the whole module: one linearly independent path, plus one per branch."""
    total = 1
    for node in ast.walk(ast.parse(module_source)):
        if isinstance(node, DECISION_POINTS):
            total += 1
        elif isinstance(node, ast.BoolOp):
            total += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            total += 1 + len(node.ifs)
    return total


def maintainability_index(module_source: str):
    """Coleman-Oman index rescaled to 0-100, where higher is more maintainable."""
    volume = halstead_metrics(module_source)["volume"]
    comments = len(comments_and_docstrings(module_source))
    sloc = len(module_source.split("\n")) - len(empty_lines(module_source)) - comments
    if sloc <= 0 or volume <= 0:
        return 100.0
    raw = (
        171
        - 5.2 * log(volume)
        - 0.23 * cyclomatic_complexity(module_source)
        - 16.2 * log(sloc)
        + 50 * sin(sqrt(2.4 * comments / sloc))
    )
    return min(100.0, max(0.0, raw * 100 / 171))


def _import_names(code):
    """Dotted names a code object imports, e.g. `from a.b import c` -> a, a.b, a.b.c."""
    for name, level, fromlist in dis._find_imports(code):
        yield name
        for item in fromlist or ():
            if item != "*":
                yield f"{name}.{item}"
    for const in code.co_consts:
        if isinstance(const, type(code)):
            yield from _import_names(const)


def _resolve(name, search):
    """Deepest importable spec for a dotted name, walking package search
    locations without importing/executing anything."""
    spec, parts = None, name.split(".")
    for i in range(len(parts)):
        locations = spec.submodule_search_locations if spec else search
        try:
            found = locations and importlib.machinery.PathFinder.find_spec(".".join(parts[: i + 1]), locations)
        except KeyError:
            found = None
        if not found:
            break
        spec = found
    return spec


def imports(module_path, root=None):
    """Full filesystem paths of the local modules `module_path` imports."""
    path = Path(module_path).resolve()
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    root = Path(root).resolve() if root else path.parent
    # an installed copy of the analyzed package must never shadow the actual local file being analyzed
    search = [str(root), *(str(d) for d in root.rglob("*") if d.is_dir())] + sys.path
    names = {n for n in _import_names(code) if n.split(".")[0] not in sys.builtin_module_names}
    specs = (_resolve(n, search) for n in names)
    return sorted({Path(s.origin).as_posix() for s in specs if s and s.origin})


def analyze_module(path, root=None):
    pth = Path(path).resolve()
    st = pth.read_text(encoding="utf-8")
    total, empty, comments = (
        len(st.split("\n")),
        len(empty_lines(st)),
        len(comments_and_docstrings(st)),
    )
    return {
        "imports": imports(pth, root),
        "total_lines": total,
        "empty_lines": empty,
        "comments": comments,
        "code_length": total - empty - comments,
        "contained_function_length": sorted(
            [len(f.split("\n")) - len(empty_lines(f)) - len(comments_and_docstrings(f)) for f in functions(st)]
        ),
        "halstead_metrics": halstead_metrics(st),
        "maintainability_index": round(maintainability_index(st), 1),
    }


def normalized_path_list(path: str):
    suffixes = Path(path).suffixes
    name = Path(path).name
    path_list = path.split("/")[:-1]
    for suff in suffixes:
        name = name.replace(suff, "")
    return path_list + [name]


def shorten(path: Path, root: Path):
    ANON_BASES = (
        (sysconfig.get_paths()["stdlib"], "<stdlib>/"),
        (sysconfig.get_paths()["purelib"], "<site-packages>/"),
        (Path.home(), "~/"),
    )
    for base, tag in ((root, ""), *ANON_BASES):
        if path.is_relative_to(base):
            return tag + path.relative_to(base).as_posix()
    return path.as_posix()


def is_valid(module_path: str, include_only, exclude):
    pathlist = normalized_path_list(module_path)
    included = not include_only or set(pathlist).isdisjoint(set(include_only))
    excluded = exclude and set(pathlist).isdisjoint(set(exclude))
    return included and not excluded


def advanced_analysis(package_data: dict):
    return {
        "total_lines": sum(d["total_lines"] for d in package_data.values()),
        "total_functions": sum(len(d["contained_function_length"]) for d in package_data.values()),
        "total_modules": len(package_data.keys()),
        "total_man_hours": int(
            round(
                sum(d["halstead_metrics"]["time"] for d in package_data.values()) / 3600,
            )
        ),
    }


def analyze_package(path, exclude=(), include_only=(), max_recursion=25):
    module_dict = {}
    resolved_path = Path(path)
    for p in resolved_path.rglob("*.py"):
        if not is_valid(p.as_posix(), exclude, include_only):
            continue
        module_data = analyze_module(p, root=resolved_path)
        module_data["imports"] = [
            imp_mod for imp_mod in module_data["imports"] if is_valid(imp_mod, exclude, include_only)
        ]
        module_dict[p.resolve().as_posix()] = module_data
        for imp in set(module_data["imports"]).difference(set(module_dict.keys())):
            module_data = analyze_module(imp, root=resolved_path)
            module_data["imports"] = [
                imp_mod for imp_mod in module_data["imports"] if is_valid(imp_mod, exclude, include_only)
            ]
            module_dict[imp] = module_data
    return {"analytics": advanced_analysis(module_dict), "modules": module_dict}
