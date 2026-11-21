from lark import Lark, Transformer, Tree, v_args
from lark.indenter import PythonIndenter

parser = Lark.open(
    "pust.lark",
    rel_to=__file__,
    parser="lalr",
    postlex=PythonIndenter(),
    start="file_input",
)


def indent(text):
    return "\n".join("    " + line for line in text.split("\n"))


def find_variadic(tree):
    """Map function name -> number of fixed params, for every def that has *args."""
    result = {}
    for node in tree.iter_subtrees():
        if node.data == "funcdef":
            name, params = node.children[0].children[0], node.children[1]
            if params is None:
                continue
            kinds = [c.data for c in params.children if isinstance(c, Tree)]
            if "starparams" in kinds:
                result[str(name)] = len(kinds) - 1
    return result


RUST_CMP = {"<": "<", ">": ">", "==": "==", ">=": ">=", "<=": "<=", "!=": "!="}


@v_args(inline=True)
class Pust(Transformer):
    def __init__(self, variadic=None) -> None:
        super().__init__()
        self.missings = {}
        self.variadic = variadic or {}

    # ---------- helpers ----------

    def chain(self, *c, mode=0):
        if mode == 0:
            try:
                result = c[0]
                for i in range(1, len(c), 2):
                    result = f"{result} {c[i]} {c[i + 1]}"
                return result
            except IndexError:
                print(f"Out of Index using safe mod: {c}")
                result = c[0]
                for i in range(1, len(c)):
                    result = f"{result} {c[i]}"
                return result
        elif mode == 1:
            result = c[0]
            for i in range(1, len(c)):
                result = f"{result}, {c[i]}"
            return result
        elif mode == 2:
            result = c[0]
            for i in range(1, len(c)):
                if c[i] == None:
                    continue
                result = f"{result}, {c[i]}"
            return result

    def notimp(self, msg):
        raise NotImplementedError(msg)

    # ---------- assignment ----------

    def annassign(self, target, type_, val):
        if val is None:  # x: i32  (değersiz bildirim)
            return f"let mut {target}: {type_};"
        return f"let mut {target}: {type_} = {val};"

    def assign_stmt(self, s):
        return s

    def assign(self, *c):
        *target, val = c
        return "\n".join(f"{h} = {val};" for h in target)

    # ---------- file / suite ----------

    def file_input(self, *s):
        return "\n".join(map(str, s))

    def suite(self, *stmts):
        return "\n".join(map(str, stmts))

    # ---------- identifiers / literals ----------

    def var(self, n):
        return n

    def name(self, n):
        return str(n)

    def number(self, n):
        return str(n)

    def getitem(self,name,index):
        return f"{name}[{index}]"

    # ---------- arithmetic ----------

    def arith_expr(self, *c):
        return f"({self.chain(*c)})"  # +  -

    def term(self, *c):
        return f"({self.chain(*c)})"  # *  /  %  //

    def power(self, val, val2):
        self.notimp("\n' ** ' ( power )\n has no direct equivalent")

    # ---------- BITWISE ----------

    def or_expr(self, val, val2):
        return f"{val} | {val2}"

    def and_expr(self, val, val2):
        return f"{val} & {val2}"

    def xor_expr(self, val, val2):
        return f"{val} ^ {val2}"

    # ---------- SHIFT ----------
    def shift_expr(self, *c):
        return f"({self.chain(*c)})"

    # ---------- logical operators ----------

    def not_test(self, val):
        return f"!{val}"

    def and_test(self, val, val2):
        return f"{val} && {val2}"

    def or_test(self, val, val2):
        return f"{val} || {val2}"

    # ---------- comparisons ----------

    def comp_op(self, *ops):
        op = " ".join(map(str, ops))
        if op not in RUST_CMP:
            self.notimp(f"'{op}' has no Rust equivalent")
        return RUST_CMP[op]

    def comparison(self, first, *rest):
        parts, left = [], first
        for i in range(0, len(rest), 2):
            op, right = rest[i], rest[i + 1]
            parts.append(f"{left} {op} {right}")
            left = right
        if len(parts) == 1:
            return parts[0]
        return " && ".join(f"({p})" for p in parts)

    # ---------- if / elif / else ----------

    def elif_(self, condition, body):
        return f" else if {condition} {{\n{indent(body)}\n}}"

    def elifs(self, *branches):
        return "".join(branches)

    def if_stmt(self, condition, body, elifs, else_body=None):
        out = f"if {condition} {{\n{indent(body)}\n}}{elifs}"
        if else_body is not None:
            out += f" else {{\n{indent(else_body)}\n}}"
        return out

    # ---------- FUNC ----------

    def funcdef(self, name, args, returntype, code):
        if args == None:
            args = ""

        if returntype == None:
            returntype = ""
        else:
            return f"fn {name}({args}) -> {returntype}" + "{\n" + f"{code}" + "\n}"
        return f"fn {name}({args})" + "{\n" + f"{code}" + "\n}"

    def expr_stmt(self, val):
        return val

    def funccall(self, name, args=None):
        args = args or []
        fixed = self.variadic.get(str(name))
        if fixed is not None:
            rest = ", ".join(map(str, args[fixed:]))
            args = args[:fixed] + [f"&[{rest}]"]
        return f"{name}({', '.join(map(str, args))})"

    def return_stmt(self, returnval):
        return f"return {returnval};"

    def arguments(self, *c):
        return list(c)

    def typedparam(self, *c):
        if len(c) == 2:
            return f"{c[0]}:{c[1]}"

    def parameters(self, *c):
        return self.chain(*c, mode=2)

    def starparam(self, param):
        name, type_ = param.split(":", 1)
        return f"{name}: &[{type_.strip()}]"

    def starparams(self, star, post):
        return star

    def poststarparams(self, *c):
        if any(x is not None for x in c):
            self.notimp("parameters after *args are not supported")

    # ---------- fallback / missing rules ----------

    def __default__(self, data, children, meta):
        self.missings.setdefault(str(data), getattr(meta, "line", "?"))
        return Tree(data, children, meta)


code = """
def main():
    x: i32 = 10
    y: i32 = 20

    if x == 10 or y == 20:
        x = 2 | 4
        y = x & y
        x = y ^ x * 2
        y = (x >> 2) ^ y << x
        x = y * 2
        y = 2+2*2
    test(0xBEEF,1,2,3,4)

def test(b:i64,c:i64,*d:u64) -> i64:
    return a + b * d[0 + 1]
"""

tree = parser.parse(code)
p = Pust(variadic=find_variadic(tree))
out = p.transform(tree)
print(out)
print(f"\n\nunknowns: {p.missings}")
