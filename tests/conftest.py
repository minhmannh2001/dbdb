# Shared fixtures for DBDB rebuild tests (add as needed).

pytest_plugins = [
    "step_defs.common_steps",
    "step_defs.smoke_steps",
    "step_defs.storage_steps",
    "step_defs.value_ref_steps",
    "step_defs.binary_node_steps",
    "step_defs.persistence_steps",
    "step_defs.interface_steps",
]
