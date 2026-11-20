from lark import Lark, Transformer, v_args,Tree
from lark.indenter import PythonIndenter

parser = Lark.open("pust.lark", rel_to=__file__, parser="lalr",
                   postlex=PythonIndenter(), start="file_input")

@v_args(inline=True)
class Pust(Transformer):
    def __init__(self) -> None:
        super().__init__()
        self.missings = {}
    
    def chain(self, *c):
        result = c[0]                     
        for i in range(1, len(c), 2):
            result = f"({result} {c[i]} {c[i + 1]})"
        return result
    
    def annassign(self,target,type_,val):
        return f"let mut {target}: {type_} = {val}"
    def assign_stmt(self, s):  return s
    def file_input(self, *s):  return "\n".join(map(str, s))
    def var(self, n):          return n
    def name(self, n):         return str(n)
    def number(self, n):       return str(n)
    def arith_expr(self, *c):  return self.chain(*c)   # +  -
    def term(self, *c):        return self.chain(*c)   # *  /  %  //
    def __default__(self, data, children, meta):
        self.missings.setdefault(str(data), getattr(meta, "line", "?"))
        return Tree(data, children, meta)
    
code = "x: int32 = 10 + (5*5)\n"

tree = parser.parse(code)
p = Pust()
out = p.transform(tree)
print(out)
print(p.missings)