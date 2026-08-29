"""Service layer for the Kopargaon CRPP backend.

Routers stay thin: they validate input and delegate here. Every function in this
package is importable without FastAPI so it can be unit-tested directly.
"""
