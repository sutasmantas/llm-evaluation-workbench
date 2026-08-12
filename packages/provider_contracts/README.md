# ProofGrid provider contracts

A small, vendor-neutral boundary for non-streaming chat completions. It
preserves ordered messages and provider-reported usage, normalizes transport
failures, and supplies an explicit offline replay provider that never falls
through to a live request on a cache miss.

This package deliberately does not implement native tool calling, streaming,
or a provider-specific CLI.

