# twingate-bootstrap

The cloud-neutral part of a connector: the Twingate connector, its tokens, and
the cloud-init that hardens the machine and installs the connector. It creates
no cloud resource. Every provider's connector module calls it and passes
`user_data` to its machine unmodified; `tests/test_module_policy.py` enforces
that. Its tests (in `tests/`) are the behavior tests for the hardening.

Outputs: `name`, and `user_data` (sensitive: it contains the connector tokens).
