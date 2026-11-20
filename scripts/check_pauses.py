"""Audit the manual pause locations in a Bambu Studio by-layer slice."""
import argparse
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

@contextmanager
def plate_stream(path, plate):
    if path.suffix.lower()==".3mf":
        with ZipFile(path) as bundle:
            members=[i for i in bundle.infolist() if i.filename==f"Metadata/plate_{plate}.gcode"]
            if len(members)!=1:
                raise ValueError(f"Expected one sliced G-code member for plate {plate}; export a sliced plate or check its number")
            with bundle.open(members[0]) as stream:
                yield stream
    elif path.suffix.lower()==".gcode" and plate==1:
        with path.open("rb") as stream:
            yield stream
    else:
        raise ValueError("Use a sliced .3mf or a plain .gcode; a standalone file contains one plate (use --plate 1)")


def scan(stream):
    generated=False
    mode=None
    expected_count=None
    in_code=False
    ended=False
    machine_end=False
    layer=0
    z=None
    conditions=0
    marker=None
    events=[]
    unknown=[]
    layers={}
    for n,raw in enumerate(stream,1):
        line=raw.decode("utf-8-sig").strip()
        if re.fullmatch(r";\s*BambuStudio\s+\S+.*",line):
            generated=True
        if line.startswith("; print_sequence ="):
            mode=line.partition("=")[2].strip()
        if line.startswith("; total layer number:"):
            expected_count=int(line.partition(":")[2])
        if line=="; EXECUTABLE_BLOCK_START":
            if in_code or ended:
                raise ValueError("Multiple executable blocks")
            in_code=True
        if not in_code:
            continue
        if line=="; MACHINE_END_GCODE_START":
            machine_end=True
        if line in {"; CUSTOM_GCODE","; CUSTOM_G_CODE","; CUSTOM_GCODE_START"}:
            unknown.append({"line":n,"reason":"custom G-code section requires profile review"})
        if line=="; CHANGE_LAYER" or line=="; EXECUTABLE_BLOCK_END":
            if marker:
                unknown.append({"line":marker,"reason":"pause marker without a confirmed manual pause"})
                marker=None
            if line.endswith("_END"):
                in_code=False
                ended=True
            else:
                layer+=1
                z=None
            continue
        if line.startswith("; Z_HEIGHT:"):
            z=Decimal(line.partition(":")[2].strip())
            if not z.is_finite() or z<=0 or layer==0 or layer in layers:
                raise ValueError("Invalid or ambiguous layer height")
            layers[layer]=z
            continue
        if line=="; PAUSE_PRINTING":
            if marker:
                unknown.append({"line":marker,"reason":"repeated pause marker"})
            marker=n
            continue
        code=line.partition(";")[0].strip().upper()
        if not code:
            continue
        cmd=code.split()[0]
        if cmd=="M622":
            conditions+=1
        elif cmd=="M623":
            conditions=max(0,conditions-1)
        if re.fullmatch(r"M400\s+U1(?:\.0+)?",code):
            marker=None
            if conditions or layer==0 or z is None or machine_end:
                unknown.append({"line":n,"command":code,"reason":"conditional or outside a known layer"})
            else:
                events.append({"layer":layer,"z_mm":str(z),"line":n})
        elif cmd in {"M0","M00","M1","M01","M25","M226","M600","M601","PAUSE","M291"} or (
            cmd=="M400" and re.search(r"\bU",code)) or re.fullmatch(r"[A-Z_][A-Z_0-9]*",cmd) and not re.fullmatch(r"[GMT]\d+",cmd):
            unknown.append({"line":n,"command":code,"reason":"custom or unverified pause behavior"})
            marker=None
    if not generated or not ended or mode!="by layer":
        raise ValueError("Expected a complete by-layer Bambu Studio export with header, print_sequence and executable block")
    if len(layers)!=layer or not layer or expected_count!=layer or list(layers.values())!=sorted(set(layers.values())):
        raise ValueError("Layer markers, height ordering or header count are inconsistent")
    return events,unknown,layers


def compare(events,unknown,layers,expected,field):
    counts=Counter(expected)
    matched=[]
    extra=[]
    for event in events:
        value=event["layer"] if field=="layer" else Decimal(event["z_mm"])
        if counts[value]:
            counts[value]-=1
            matched.append(event)
        else:
            extra.append(event)
    missing=list(counts.elements())
    visible=lambda v: int(v) if field=="layer" else str(v)
    report={"status":"inconclusive" if unknown else "review" if missing or extra else "match",
            "compared_by":field,"layer_count":len(layers),"matched":matched,
            "missing":[visible(v) for v in missing],"unexpected":extra,"unverified":unknown}
    if len(missing)==len(extra)==1:
        actual=extra[0]["layer"] if field=="layer" else Decimal(extra[0]["z_mm"])
        report["unexpected_minus_expected"]=visible(actual-missing[0])
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("file",type=Path)
    p.add_argument("--plate",type=int,default=1)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--height",action="append",metavar="MM")
    group.add_argument("--layer",type=int,action="append",metavar="N")
    group.add_argument("--expect-none",action="store_true")
    a=p.parse_args()
    try:
        expected=[Decimal(s) for s in a.height] if a.height else a.layer or []
        if a.plate<1 or any(not Decimal(v).is_finite() or v<=0 for v in expected):
            raise ValueError("Plate, layers and heights must be positive finite values")
        with plate_stream(a.file,a.plate) as stream:
            events,unknown,layers=scan(stream)
        report=compare(events,unknown,layers,expected,"layer" if a.layer else "z_mm")
        report["plate"]=a.plate
    except (OSError,ValueError,BadZipFile,RuntimeError,InvalidOperation) as exc:
        p.exit(2,f"Cannot verify: {exc}\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report["status"]=="match" else 1)
