"""SVG helpers for poster figures. Styling comes from CSS classes in the template:
b (box), ba (accent box), bd (dashed), bo (outline), a/l (arrow/line), la (accent line),
v (accent dashed curve), sep, dash; text classes t (small caps), it (italic)."""
def box(x,y,w,h,label=None,cls="b",fs=11,dy=0):
    s=f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="2"/>'
    if label is not None:
        lines=label.split("|")
        n=len(lines); lh=fs*1.15
        y0=y+h/2-(n-1)*lh/2+fs*0.35+dy
        for i,l in enumerate(lines):
            s+=f'<text x="{x+w/2}" y="{y0+i*lh}" font-size="{fs}" text-anchor="middle">{l}</text>'
    return s
def arr(x1,y1,x2,y2,cls="a"):
    return f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" marker-end="url(#ah)"/>'
def ln(x1,y1,x2,y2,cls="l"):
    return f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
def txt(x,y,t,fs=11,anchor="middle",cls=""):
    return f'<text class="{cls}" x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}">{t}</text>'
def svg(w,h,body):
    d='<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" class="mk"/></marker><marker id="aho" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" class="mko"/></marker></defs>'
    return f'<svg class="fig" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{d}{body}</svg>'

