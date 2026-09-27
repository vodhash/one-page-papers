"""The arrow diagram of p. 30: each pollen cell joins one germ cell."""
from svg import arr, txt, svg

def befruchtung():
    xs=[150,205,245,300]; top=["A","A","a","a"]; s=""
    s+=txt(118,22,"Pollenzellen",13,"end")
    s+=txt(118,98,"Keimzellen",13,"end")
    for x,l in zip(xs,top):
        s+=txt(x,22,l,14,cls="it")
        s+=txt(x,98,l,14,cls="it")
    s+=arr(xs[0],32,xs[0],80)
    s+=arr(xs[3],32,xs[3],80)
    s+=arr(xs[1],32,xs[2],80)
    s+=arr(xs[2],32,xs[1],80)
    return svg(330,108,s)

FIGS={"befruchtung":befruchtung}
