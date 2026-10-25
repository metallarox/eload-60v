import re

TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse(text):
    stack = [[]]
    for m in TOK.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t)
    return stack[0]


def dump(x, ind=0):
    if not isinstance(x, list):
        return x
    if all(not isinstance(e, list) for e in x):
        return '(' + ' '.join(x) + ')'
    parts = []
    head = []
    for e in x:
        if isinstance(e, list):
            parts.append(dump(e, ind + 1))
        elif not parts:
            head.append(e)
        else:
            parts.append(e)
    pad = '\n' + '  ' * (ind + 1)
    return '(' + ' '.join(head) + pad + pad.join(parts) + ')'


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def uq(s):
    if s.startswith('"'):
        return s[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    return s


def find(node, key):
    return [e for e in node if isinstance(e, list) and e and e[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None
