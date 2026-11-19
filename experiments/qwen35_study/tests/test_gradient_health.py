import math
from types import SimpleNamespace
import unittest

from experiments.qwen35_study.gradients import gradient_health, require_finite_gradients


class TensorResult:
    def __init__(self, value):
        self.value = value

    def all(self):
        return self

    def item(self):
        return self.value


TORCH = SimpleNamespace(isfinite=lambda xs: TensorResult(all(map(math.isfinite, xs))),
                        count_nonzero=lambda xs: TensorResult(sum(x != 0 for x in xs)))


class GradientHealth(unittest.TestCase):
    def parameters(self, *grads):
        return [SimpleNamespace(requires_grad=True, grad=g) for g in grads]

    def test_missing_gradients_cannot_pass(self):
        health = gradient_health(self.parameters(None, None), TORCH)
        self.assertEqual(health['missing_gradient_tensors'], 2)
        with self.assertRaisesRegex(ValueError, 'Missing'):
            require_finite_gradients(health)

    def test_nonfinite_gradients_cannot_be_ignored(self):
        health = gradient_health(self.parameters([1.0], [float('inf')], [float('nan')]), TORCH)
        self.assertEqual(health['nonfinite_gradient_tensors'], 2)
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            require_finite_gradients(health)

    def test_finite_zero_gradients_are_valid_but_not_nonzero(self):
        health = gradient_health(self.parameters([0.0], [1.0], None), TORCH)
        require_finite_gradients(health)
        self.assertEqual(health['gradient_tensors'], 2)
        self.assertEqual(health['nonzero_gradient_tensors'], 1)
