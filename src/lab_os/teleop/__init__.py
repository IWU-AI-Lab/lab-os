"""Teleop module: Quest (or any XR input) → arm, live.

Pipeline: WebXR page → WebSocket (`server.py`) → latest `XRFrame` → `TeleopLoop` (`loop.py`)
→ `ClutchMapper` (`mapping.py`) → `Arm`. Message format: docs/protocol.md.
"""
