"""hcns_eval — pipeline-agnostic evaluation framework for HC-NS KB.

The harness depends only on the PipelineAdapter Protocol (hcns_shared); concrete
pipelines are wrapped by adapters in the adapters/ module so this package never
imports pipeline internals directly.
"""
