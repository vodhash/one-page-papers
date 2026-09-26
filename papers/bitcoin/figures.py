"""Vector redraws of the 7 figures of the Bitcoin whitepaper."""
from svg import box, arr, ln, txt, svg

def transactions():
    s=""; xs=[12,167,322]; W=106
    for i,x in enumerate(xs):
        s+=box(x,8,W,150,cls="bo")
        s+=txt(x+W/2,24,"Transaction",10.5,cls="t")
        s+=box(x+8,32,W-16,32,f"Owner {i+1}’s|Public Key",fs=10)
        s+=box(x+8,80,W-16,22,"Hash",fs=10.5,cls="ba")
        s+=box(x+8,118,W-16,32,f"Owner {i}’s|Signature",fs=10)
        s+=arr(x+W/2,64,x+W/2,78)
        s+=arr(x+W/2,102,x+W/2,116)
        s+=box(x+8,196,W-16,32,f"Owner {i}’s|Private Key",fs=10,cls="bd")
        s+=arr(x+W/2,196,x+W/2,152)
        s+=txt(x+W/2+4,177,"Sign",9.5,"start",cls="it")
        if i<2:
            nx=xs[i+1]
            s+=arr(x+W,91,nx+6,91)
            s+=f'<path class="v" d="M{nx+8},134 C{nx-22},134 {x+W+30},48 {x+W-10},48" marker-end="url(#aho)"/>'
            s+=txt((x+W+nx)/2,122,"Verify",9.5,cls="it")
    return svg(440,236,s)

def timestamp():
    s=""
    for x in (40,250):
        s+=box(x,10,130,28,"Hash",cls="ba")
        s+=box(x-10,78,150,46,cls="bo")
        s+=txt(x-2,90,"Block",9.5,"start",cls="t")
        s+=box(x,98,42,20,"Item",fs=9.5)+box(x+50,98,42,20,"Item",fs=9.5)+txt(x+114,112,"…",11)
        s+=arr(x+65,78,x+65,40)
    s+=arr(2,24,38,24)+arr(170,24,248,24)+arr(380,24,436,24)
    return svg(440,132,s)

def pow_():
    s=""
    for x in (14,232):
        s+=box(x,8,194,98,cls="bo")
        s+=txt(x+8,22,"Block",9.5,"start",cls="t")
        s+=box(x+10,30,96,26,"Prev Hash",fs=10.5,cls="ba")+box(x+114,30,70,26,"Nonce",fs=10.5)
        s+=box(x+10,68,50,26,"Tx",fs=10.5)+box(x+68,68,50,26,"Tx",fs=10.5)+txt(x+150,86,"…",12)
    s+=arr(0,43,22,43)+arr(208,43,240,43)+arr(426,43,440,43)
    return svg(440,112,s)

def tree(x0,full):
    s=""; W=205; cx=x0+W/2
    s+=box(x0,8,W,222,cls="bo")
    s+=box(x0+10,18,W-20,76,cls="bd")
    s+=txt(x0+18,32,"Block Header (Block Hash)",9,"start",cls="t")
    s+=box(x0+20,40,80,20,"Prev Hash",fs=9.5)+box(x0+108,40,77,20,"Nonce",fs=9.5)
    s+=box(cx-40,68,80,20,"Root Hash",fs=9.5,cls="ba")
    L2=[x0+30,x0+115]; bw=60
    s+=box(L2[0],110,bw,20,"Hash01",fs=9.5)+box(L2[1],110,bw,20,"Hash23",fs=9.5)
    for x in L2: s+=ln(cx,88,x+bw/2,110)
    L3=[x0+12,x0+58,x0+104,x0+150]; b3=43
    names=["Hash0","Hash1","Hash2","Hash3"]
    for j,x in enumerate(L3):
        if full or j>=2:
            s+=box(x,152,b3,20,names[j],fs=8.8)+ln(L2[j//2]+bw/2,130,x+b3/2,152)
        if full or j==3:
            s+=box(x,194,b3,20,f"Tx{j}",fs=9)+ln(x+b3/2,172,x+b3/2,194)
    return s
def reclaim():
    s=tree(12,True)+tree(223,False)
    s+=txt(114,250,"Transactions Hashed in a Merkle Tree",10,cls="it")
    s+=txt(325,250,"After Pruning Tx0-2 from the Block",10,cls="it")
    return svg(440,258,s)

def spv():
    s=txt(220,14,"Longest Proof-of-Work Chain",10.5,cls="t")
    xs=[10,155,300]; W=130
    for x in xs:
        s+=box(x,22,W,74,cls="bo")
        s+=txt(x+8,35,"Block Header",9,"start",cls="t")
        s+=box(x+8,42,62,20,"Prev Hash",fs=9)+box(x+76,42,46,20,"Nonce",fs=9)
        s+=box(x+20,68,90,20,"Merkle Root",fs=9,cls="ba" if x==155 else "b")
    s+=arr(140,52,161,52)+arr(285,52,306,52)+arr(430,52,440,52)
    mx=220
    s+=f'<rect class="dash" x="150" y="112" width="140" height="102" rx="4"/>'
    s+=box(160,122,56,20,"Hash01",fs=9)+box(224,122,56,20,"Hash23",fs=9,cls="ba")
    s+=ln(mx,88,188,122)+ln(mx,88,252,122,"la")
    s+=box(196,154,44,20,"Hash2",fs=9)+box(246,154,40,20,"Hash3",fs=9,cls="ba")
    s+=ln(252,142,218,154)+ln(252,142,266,154,"la")
    s+=box(246,186,40,20,"Tx3",fs=9,cls="ba")+ln(266,174,266,186,"la")
    s+=txt(298,200,"Merkle Branch for Tx3",10,"start",cls="it")
    return svg(440,222,s)

def combine():
    s=box(140,6,160,96,cls="bo")+txt(220,21,"Transaction",10.5,cls="t")
    for y,l in ((32,"In"),(56,"In"),(80,"…")):
        s+=box(152,y,46,18,l,fs=10)+arr(100,y+9,150,y+9)
    for y,l in ((32,"Out"),(56,"…")):
        s+=box(242,y,46,18,l,fs=10)+arr(288,y+9,338,y+9)
    return svg(440,108,s)

def privacy():
    s=txt(6,14,"Traditional Privacy Model",10.5,"start",cls="t")
    xs=[6,92,178,264]; w=74
    labs=["Identities","Transactions","Trusted|Third Party","Counterparty"]
    for x,l in zip(xs,labs): s+=box(x,22,w,36,l,fs=9.8)
    for i in range(3): s+=arr(xs[i]+w,40,xs[i+1]-1,40)
    s+=ln(350,16,350,66,"sep")+box(362,22,72,36,"Public",fs=9.8,cls="ba")
    s+=txt(6,94,"New Privacy Model",10.5,"start",cls="t")
    s+=box(6,102,74,36,"Identities",fs=9.8)+ln(92,96,92,146,"sep")
    s+=box(104,102,86,36,"Transactions",fs=9.8)+arr(190,120,360,120)
    s+=box(362,102,72,36,"Public",fs=9.8,cls="ba")
    return svg(440,148,s)

FIGS={"transactions":transactions,"timestamp":timestamp,"proof-of-work":pow_,
"reclaiming-disk":reclaim,"spv":spv,"combining-splitting":combine,"privacy":privacy}
