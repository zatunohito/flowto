"""print scene start times (minutes) per chapter to choose PARTS split points"""
import json, glob, os, sys
OUT = os.environ.get("MV_OUT", "/tmp/claude-0/-home-user-flowto/822ad1fa-d985-5ed3-936a-0b5a6da616d3/scratchpad/work/out")
for p in sorted(glob.glob(os.path.join(OUT, "ch[0-9][0-9].json"))):
    d = json.load(open(p))
    print(f"== {os.path.basename(p)[:-5]}  {d['duration']/60:.1f} min  {d['title']}")
    for i, (t, st) in enumerate(d["scenes"]):
        print(f"   {i:2d} {st/60:5.1f}  {t}")
