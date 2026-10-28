"""Exact learned-value comparison, independent of pickle memoization and array padding."""
import pickle

import numpy as np


def same_model_state(left, right):
    # Keep strong references: temporary RNG state dictionaries must not reuse visited IDs.
    seen={}

    def same(a,b):
        if a is b or (id(a),id(b)) in seen:
            return True
        seen[id(a),id(b)]=(a,b)
        if type(a)!=type(b):
            return False
        if isinstance(a,np.ndarray):
            return a.dtype==b.dtype and np.array_equal(a,b)
        if isinstance(a,np.random.Generator):
            return same(a.bit_generator.state,b.bit_generator.state)
        if isinstance(a,dict):
            return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
        if isinstance(a,(list,tuple)):
            return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
        if isinstance(a,(str,int,float,bool,type(None),np.generic,set,frozenset)):
            return bool(a==b)
        if hasattr(a,'__dict__'):
            return same(vars(a),vars(b))
        return pickle.dumps(a)==pickle.dumps(b)

    return same(left,right)
