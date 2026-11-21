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


RUST_CMP = {"<": "<", ">": ">", "==": "==", ">=": ">=", "<=": "<=", "!=": "!="}


@v_args(inline=True)
class Pust(Transformer):
    def __init__(self) -> None:
        super().__init__()
        self.missings = {}

    # ---------- helpers ----------

    def chain(self, *c):
        result = c[0]
        for i in range(1, len(c), 2):
            result = f"({result} {c[i]} {c[i + 1]})"
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

    # ---------- arithmetic ----------

    def arith_expr(self, *c):
        return self.chain(*c)  # +  -

    def term(self, *c):
        return self.chain(*c)  # *  /  %  //

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
        return self.chain(*c)

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
        else:
            self.notimp("Sorry no function arg support yet")
        if returntype == None:
            returntype = ""
        else:
            return f"fn {name}({args}) -> {returntype}" + "{\n" + f"{code}" + "\n}"
        return f"fn {name}({args})" + "{\n" + f"{code}" + "\n}"

    def expr_stmt(self, val):
        return val

    def funccall(self, name, args):
        if args == None:
            return f"{name}();"
        else:
            return f"{name}({args});"

    def return_stmt(self, returnval):
        return f"return {returnval};"

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
    test()

def test() -> i64:
    return 0xDEADBEEF
"""

tree = parser.parse(code)
p = Pust()
out = p.transform(tree)
print(out)
print(f"\n\nunknowns: {p.missings}")
