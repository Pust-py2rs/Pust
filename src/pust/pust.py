import ast

OPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


class Pust:
    def __init__(self, code):
        self.tree = ast.parse(code)
        self.vars = set()

    def run(self):
        return self.classify(self.tree)

    # ---------- router ----------
    def classify(self, n):
        match n:
            case ast.Module(body=body):
                return self.body(body)
            case ast.Assign(targets=[ast.Name(id=name)], value=v):
                return self.assign(name, v)
            case ast.Expr(value=v):
                return self.classify(v) + ";"
            case ast.Call(func=ast.Name(id=name), args=args):
                return self.call(name, args)
            case ast.BinOp(left=l, op=o, right=r) if type(o) in OPS:
                return self.binop(l, o, r)
            case ast.Constant(value=v):
                return str(v)
            case ast.Name(id=name):
                return name
            case _:
                raise NotImplementedError(ast.dump(n))

    # ---------- things ----------
    
    def body(self, bd):
        satirlar = "\n".join(
            "    " + l for s in bd for l in self.classify(s).split("\n")
        )
        return "fn main() {\n" + satirlar + "\n}"

    def assign(self, name, v):
        deger = self.classify(v)
        if name in self.vars:
            return f"{name} = {deger};"
        self.vars.add(name)
        return f"let mut {name} = {deger};"

    def call(self, name, args):
        a = [self.classify(x) for x in args]
        match (name, a):
            case ("print", []):
                return "println!()"
            case ("print", [x]):
                return f'println!("{{}}", {x})'
            case _:
                return f"{name}({', '.join(a)})"

    def binop(self, l, o, r):
        return f"({self.classify(l)} {OPS[type(o)]} {self.classify(r)})"


print(Pust("x = 10 * 3\ny = x + 5\nprint(y)").run())
