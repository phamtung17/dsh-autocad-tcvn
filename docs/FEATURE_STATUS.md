# CAD Agent v1.1 — implementation vs verification

| Feature | Implemented | Evidence and limits |
|---|---|---|
| 2D LINE, POLYLINE, CIRCLE, ARC, TEXT, MTEXT | Yes COM/DXF | Offline DXF+mock COM; AutoCAD Windows test pending |
| Aligned, rotated, radial, diameter dimensions | Yes COM/DXF | Mock API; real dimensions measured in opt-in integration suite |
| Static blocks/insert | Yes | Normalized layer and base point, unique IDs; regression suite added |
| Human approval and worker permission | Yes | One-use signed permit for job; same-user arbitrary code execution not prevented |
| Quality Gate | Yes | Geometry, missing measurements, bad references, engineer review and project rules |
| Paper Space, viewport custom scale | Yes code | Offline plotting tests; actual COM and target/view position need Windows review |
| DWT template, CTB, plotter | Optional | Explicit allowlisted file, installed devices; fail closed |
| Real AutoCAD PDF file | Code written | PDF physical page check; no real plot executed here |
| DXF & schematic preview PDF | Yes | Offline, NOT TO SCALE production plot |
| TCVN standard inventory | Yes | Catalog needs revalidation |
| TCVN clause rules | Engine yes; rule verification no | Local reviewer-attested machine checks; no authentic clause pack supplied |
| 10 DSH skills | Overlay configuration written | Filesystem metadata checked; DSH live discovery not run here |
| MCP 14 tools | Source + mock registration | SDK handshake test in CI; DSH session unverified here |
| Real AutoCAD 2025 regression | Script written | Must run on Windows with AutoCAD open; creates/reopens new DWG |
| Offline pytest CI | Workflow written | No CI run yet in GitHub until pushed |
| DWG modification / 3D / engineering calculation | No | Must be separate validated modules |
