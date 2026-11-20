# Verify an insert pause before printing

Download the named ZIP under Assets on the [release page](https://github.com/Uone100/bambu-pause-check/releases/latest). Extract it and open a terminal beside `SKILL.md`. Install Python 3.9 or later. On Windows you can use `py` wherever the examples use `python`.

## Learn the three outcomes

These three inspection excerpts came from the same 8 × 8 × 3 mm model, sliced three times in Bambu Studio 02.09.01.70 using the P2S 0.4 mm profile and 0.2 mm layers. Each excerpt retains the layer and pause evidence. Use them as checker inputs only.

```sh
python scripts/check_pauses.py examples/good.gcode --height 1.0
python scripts/check_pauses.py examples/missing.gcode --height 1.0
python scripts/check_pauses.py examples/extra.gcode --height 1.0
```

| Input | Expected result |
| --- | --- |
| good | `match`. Layer 5 contains a manual pause at 1.0 mm. |
| missing | `review`. The 1.0 mm pause is missing. |
| extra | `review`. Layer 5 matches, and layer 10 has an unexpected pause at 2.0 mm. |

To reproduce a position error, run the first command with `--height 1.2`. The unexpected pause is 0.2 mm below the intended height. The signed difference is only reported when exactly one expected and one unexpected location remain.

## Check your own plate

1. In Bambu Studio, use the layer slider to identify the intended pause height or one-based layer. Re-slice after editing pauses. Export the **sliced plate** as G-code or a sliced 3MF.
2. If a sliced project contains several plates, pass the internal plate number explicitly. Raw G-code holds one plate; use its default plate number 1.
3. Supply every expected pause. For example, plate 2 needs two inserts at 6.4 and 12.0 mm:

```sh
python scripts/check_pauses.py project.gcode.3mf --plate 2 --height 6.4 --height 12.0
```

Use `--layer 32` to check a layer instead, or `--expect-none` on a design that should never pause. Heights refer to slicing layer markers and use exact decimal millimetres. They are independent of nozzle travel and Z-hop moves. Use the reported line in the extracted `Metadata/plate_N.gcode` and the corresponding layer in Studio's preview to investigate.

## Interpret the result

The reported height comes from the slicer's layer marker. Inspect that layer in Studio's preview to see where the pocket closes. A custom pause can occur partway through a layer. A pause in the machine end routine is reported as unverified.

Exit 0 means the recognized manual pauses match. Exit 1 means review or inconclusive. Exit 2 means the input could not be verified. If a plate is missing, re-export that plate with slicing data. For an unknown command, examine the reported line and your printer profile. The supported case is text G-code from Bambu Studio, by-layer sequence, using the manual pause command `M400 U1`. An ordinary `M400` waits for motion to finish. Other firmware instructions, macros and runtime printer behavior can require manual review.

For agent installation see the [README](README.md). You can ask: “Check whether plate 2 pauses exactly once at 6.4 mm. Show me the lines I should review.”
