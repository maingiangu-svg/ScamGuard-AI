"""Compare learned values without mistaking NumPy padding for changed weights."""
import unittest
import numpy as np

from model_state import same_model_state


class ModelStateTests(unittest.TestCase):
    def test_structured_array_padding_is_not_a_learned_parameter(self):
        dtype=np.dtype({'names':['value','feature'],'formats':['f8','i4'],'offsets':[0,8],'itemsize':16})
        a=np.ndarray(1,dtype=dtype,buffer=bytearray(16))
        b=np.ndarray(1,dtype=dtype,buffer=bytearray([255]*16))
        for x in [a,b]:x['value']=.25;x['feature']=7
        self.assertNotEqual(a.tobytes(),b.tobytes())
        self.assertTrue(same_model_state({'nodes':a},{'nodes':b}))
        b['value']=.5
        self.assertFalse(same_model_state({'nodes':a},{'nodes':b}))

    def test_rng_and_threshold_changes_are_detected(self):
        a=np.random.default_rng(42);b=np.random.default_rng(42)
        self.assertTrue(same_model_state(a,b))
        b.random();self.assertFalse(same_model_state(a,b))
        self.assertFalse(same_model_state({'threshold':.5},{'threshold':.6}))

    def test_cycles_are_supported_without_skipping_later_differences(self):
        a={};a['self']=a;b={};b['self']=b
        self.assertTrue(same_model_state(a,b))
        a['coef']=np.array([1.]);b['coef']=np.array([2.])
        self.assertFalse(same_model_state(a,b))


if __name__=='__main__':unittest.main()
