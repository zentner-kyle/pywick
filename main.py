#!/bin/python3

import operator


def identity(x):
    return x


class Var:

    def __init__(self, value=None, ctxt=None):
        self.value = value
        self.ctxt = ctxt
        self.ops = []

    def set(self, value, evaluator, ctxt):
        self.ctxt = Context.merge(evaluator, [self.ctxt, ctxt])
        if self.value is not None and self.value != value:
            old_value = self.value
            self.value = None
            evaluator.conflict(self.ctxt, self, old_value, value)
        else:
            self.value = value
            self.react(evaluator)

    def react(self, evaluator):
        evaluator.notify(self)

    def unify(self, other):
        Ex([self], identity, other)
        Ex([other], identity, self)


class Op:

    def __init__(self, vars, fn, out):
        self.vars = vars
        for v in self.vars:
            v.ops.append(self)
        self.fn = fn
        self.out = out

    def run(self, evaluator, ctxt):
        for var in self.vars:
            if var.value is None:
                return
        self.exec_fn(evaluator, ctxt)

    def exec_fn(self, evaluator, ctxt):
        self.fn(evaluator, ctxt, self.out, *self.vars)


class Ex(Op):

    def exec_fn(self, evaluator, ctxt):
        vals = [var.value for var in self.vars]
        self.out.set(self.fn(*vals), evaluator, ctxt)


class Group:

    def __init__(self, ops, vars):
        self.ops = ops
        self.vars = vars

    def dup(self, ctxt, inputs=()):
        op_map = {}
        var_map = {}
        for var in self.vars:
            var_map[var] = Var(var.value)
        for op in self.ops:
            op_map[op] = Op([var_map.get(v, v) for v in op.vars], op.fn,
                            var_map.get(op.out, op.out))
        outputs = []
        for i in inputs:
            if i in var_map:
                outputs.append(var_map[i])
            elif i in op_map:
                outputs.append(op_map[i])
            else:
                raise AssertionError('dup target {!r} not in group'.format(i))
        return Group(list(op_map.values()), list(var_map.values())), outputs


def conflict_helper(evaluator, ctxt, out, op, a, b):
    op.value.vars.append(a)
    op.value.vars.append(b)
    op.out = out
    op.value.run(evaluator, op.ctxt)


class Evaluator:

    def __init__(self, vars):
        self.vars = set(vars)
        for v in vars:
            if v.value is not None:
                self.vars.add(v)

    def run(self):
        while len(self.vars) > 0:
            var = self.vars.pop()
            for op in var.ops:
                op.run(self, var.ctxt)

    def notify(self, var):
        self.vars.add(var)

    def conflict(self, ctxt, var, a, b):
        # TODO(zentner): Don't make these vars from thin air.
        # This is necessary for the lazy operator to work.
        Op([ctxt.conflict, Var(a), Var(b)], conflict_helper, var)


class Context:

    def __init__(self):
        self.conflict = Var()
        self.handler = Var()

    @staticmethod
    def merge(evaluator, ctxts):
        ctxts = [ctxt for ctxt in ctxts if ctxt is not None]
        if len(ctxts) == 1:
            return ctxts[0]
        else:
            for ctxt in ctxts:
                for c in ctxts:
                    ctxt.conflict.unify(c.conflict)
                    ctxt.handler.unify(c.handler)
        if len(ctxts) > 0:
            return ctxts[0]
        else:
            return Context()


x = Var()
anon1 = Var(1)
y = Var()
Ex([anon1, y], operator.add, x)
Ex([anon1], identity, y)
Ex([x], print, Var())

Evaluator([anon1]).run()
