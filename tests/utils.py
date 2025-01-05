from dataclasses import fields


def update_config(config, **updates):
    """
    Safely update a frozen dataclass without triggering __post_init__.

    Args:
        config: Frozen dataclass instance to update.
        **updates: Field-value pairs to update.

    Returns:
        A new dataclass instance with updated fields.
    """
    cls = config.__class__
    current_values = {field.name: getattr(config, field.name) for field in fields(config)}
    current_values.update(updates)
    obj = object.__new__(cls)
    for key, value in current_values.items():
        object.__setattr__(obj, key, value)
    return obj
