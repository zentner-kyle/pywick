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
        def unify(self_or_other):
            if (isinstance(self.value, Group) and
                    isinstance(other.value, Group)):
                self.value.unify(other.value)
            return self
        Ex([self], unify, other)
        Ex([other], unify, self)

    def __repr__(self):
        if self.ctxt is None:
            return 'Var({!r})'.format(self.value)
        else:
            return 'Var({!r}, {!r})'.format(self.value, self.ctxt)


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
        evaluator.vars.add(self.out)

    def exec_fn(self, evaluator, ctxt):
        self.fn(evaluator, ctxt, self.out, *self.vars)


class Ex(Op):

    def exec_fn(self, evaluator, ctxt):
        vals = [var.value for var in self.vars]
        self.out.set(self.fn(*vals), evaluator, ctxt)


class Call:

    def __init__(self, vars, out):
        self.vars = vars
        self.out = out

    def exec_fn(self, evaluator, ctxt):
        group = self.vars[0].dup()
        args = Group()
        for i, var in enumerate(self.vars[1:]):
            args.index(i).unify(var)
            group.value.name('args').unify(args)
        group.value.name('result').unify(self.out)


class Group:

    def __init__(self, ops=None, vars=None, groups=None):
        if ops is None:
            ops = []
        if vars is None:
            vars = []
        if groups is None:
            groups = []
        self.ops = ops
        self.vars = vars
        self.groups = groups
        self.by_name = {}
        self.by_index = {}

    def name(self, name, var=None):
        if var is None:
            return self.by_name[name]
        else:
            assert var in self.vars
            assert name not in self.by_name
            self.by_name[name] = var

    def index(self, index, var=None):
        if var is None:
            return self.by_index[index]
        else:
            assert var in self.vars
            assert index not in self.by_index
            self.by_index[index] = var

    def unify(self, other_group):
        for name, var in self.by_name.items():
            var.unify(other_group.name(name))
        for index, var in self.by_index.items():
            var.unify(other_group.index(index))

    def dup(self, memo=None):
        '''Perform of the group. This is deep in the sense that it copies all
        of the variables, operators, and groups in this group. The groups are
        also dup'd recursively. However, variables and operators outside of
        this family of groups are not copied.
        '''
        if memo is None:
            memo = {}
        if self in memo:
            return memo[self]
        for var in self.vars:
            memo[var] = Var(var.value)
        for group in self.groups:
            memo[group] = group.dup(memo)
        for op in self.ops:
            memo[op] = Op([memo.get(v, v) for v in op.vars], op.fn,
                          memo.get(op.out, op.out))
        ops = [memo[op] for op in self.ops]
        vars = [memo[var] for var in self.vars]
        groups = [memo[group] for group in self.groups]
        return Group(ops, vars, groups)


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
            print('var', var)
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

a = Var()
b = Var()
one = Var(1)
two = Var(2)
Ex([b, one], operator.add, a)
Ex([b, two], operator.add, a)
Ex([a], print, Var())
v = Var()
i = Var()
j = Var()
conflict_op = Ex([i, j], min, v)
args = Group(vars=[v, i, j])
args.index(0, v)
args.index(1, i)
args.index(2, j)
args_var = Var(args)
result_var = Var()
conflict_fn = Group(vars=[args_var, result_var, v, i, j], ops=[conflict_op],
                    groups=[args])
conflict_fn.name('args', args_var)
conflict_fn.name('result', result_var)
ctxt = Context()
ctxt.conflict.unify(conflict_fn)
conflict_one = Var(1, ctxt)
Ex([conflict_one], identity, b)
Evaluator([one, two, conflict_one, a, b]).run()
