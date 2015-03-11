from collections import OrderedDict
from inspect import Parameter, signature
from itertools import chain, starmap
from operator import itemgetter

__all__ = ['namedtuple']

dict_property = property(lambda self: OrderedDict(zip(self._fields, self)),
                         doc='dictionary for instance variables (if defined)')


def assign_default(sig, bound):
    for param in sig.parameters.values():
        if param.name not in bound.arguments \
           and param.default is not param.empty:
            bound.arguments[param.name] = param.default


def str_assign(sig, self):
    bound = sig.bind(*self)
    assign_default(sig, bound)
    return ', '.join(starmap('{}={!r}'.format, bound.arguments.items()))


def namedtuple(init):
    sig = signature(init)
    name = init.__name__

    for param in sig.parameters.values():
        if param.kind != param.POSITIONAL_OR_KEYWORD:
            raise ValueError('Named tuple can only have regular arguments'
                             'that can be either positional or keyword')

    def __new__(_cls, *args, **kwargs):
        init(*args, **kwargs)
        bound = sig.bind(*args, **kwargs)
        assign_default(sig, bound)
        return tuple.__new__(_cls, bound.arguments.values())
    new_params = chain([Parameter('_cls', Parameter.POSITIONAL_OR_KEYWORD)],
                       sig.parameters.values())
    __new__.__signature__ = sig.replace(parameters=new_params)

    def _make(cls, iterable):
        'Make a new {name} object from a sequence or iterable'
        result = tuple.__new__(cls, iterable)
        if len(result) != len(sig.parameters):
            raise TypeError('Expected {expected} arguments,'
                            'got {actual}'.format(expected=len(sig.parameters),
                                                  actual=len(result)))
        return result
    _make.__doc__ = _make.__doc__.format(name=name)

    def _replace(_self, **kwds):
        'Return a new {name} object replacing specified fields with new values'
        result = _self._make(map(kwds.pop, sig.parameters.keys(), _self))
        if kwds:
            raise ValueError('Got unexpected'
                             'field names: {}'.format(', '.join(kwds)))
        return result
    _replace.__doc__ = _replace.__doc__.format(name=name)

    def repr(self):
        'x.__repr__() <==> repr(x)'
        return '{name}({args})'.format(name=name, args=str_assign(sig, self))

    @classmethod
    def _method(cls, func):
        'Assign a new method for the namedtuple class'
        setattr(cls, func.__name__, func)
        return func

    @classmethod
    def _property(cls, func):
        'Assign a new property for the namedtuple class'
        setattr(cls, func.__name__, property(func))
        return func

    dct = dict(_make=classmethod(_make),
               _fields=list(sig.parameters.keys()),
               _replace=_replace,
               _method=_method,
               _property=_property,
               __slots__=(),
               __doc__=init.__doc__ or name + str(sig),
               __new__=__new__,
               __repr__=repr,
               __getnewargs__=tuple,
               __getstate__=lambda self: None,
               __dict__=dict_property)

    for i, pname in enumerate(sig.parameters.keys()):
        dct[pname] = property(itemgetter(i),
                              doc='Alias for field number {index:d}'
                                  .format(index=i))

    return type(name, (tuple,), dct)
