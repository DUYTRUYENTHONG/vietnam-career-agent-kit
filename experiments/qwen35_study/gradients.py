"""Record gradient health without hiding missing or nonfinite backward results."""


def gradient_health(parameters, torch):
    parameters = [p for p in parameters if p.requires_grad]
    gradients = [p.grad for p in parameters if p.grad is not None]
    return {'gradient_tensors': len(gradients),
        'missing_gradient_tensors': len(parameters) - len(gradients),
        'nonfinite_gradient_tensors': sum(not torch.isfinite(g).all().item() for g in gradients),
        'nonzero_gradient_tensors': sum(torch.count_nonzero(g).item() > 0 for g in gradients)}


def require_finite_gradients(health):
    if not health['gradient_tensors']:
        raise ValueError('Missing adapter gradients')
    if health['nonfinite_gradient_tensors']:
        raise ValueError('Nonfinite adapter gradients')
