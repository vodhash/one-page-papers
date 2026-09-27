"""Vector redraw of the Figure of the eight Cova of page 88 of the 1703 Mémoires: each trigram,
the column of its digits (top line: the last digit, as printed), the number in binary and in
decimal, with the rules of the original."""
from svg import ln, txt, svg

def cova():
    W, top = 76, 14
    s = ""
    for k in range(8):
        cx = 38 + k * W
        for r in range(3):
            y = top + r * 9
            if (k >> r) & 1:
                s += f'<rect x="{cx - 24}" y="{y}" width="48" height="4.2" class="tri"/>'
            else:
                s += (f'<rect x="{cx - 24}" y="{y}" width="20" height="4.2" class="tri"/>'
                      f'<rect x="{cx + 4}" y="{y}" width="20" height="4.2" class="tri"/>')
        for r in range(3):
            s += txt(cx, 62 + r * 19, str((k >> r) & 1), fs=19)
        s += txt(cx, 138, format(k, "b"), fs=21)
        s += txt(cx, 180, str(k), fs=21)
    s += ln(4, 112, 604, 112) + ln(4, 150, 604, 150) + ln(4, 155, 604, 155)
    return svg(608, 190, s)

FIGS = {"cova": cova}
