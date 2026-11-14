import numpy as np
from collections import deque
def blobs(mask, step=4, min_area=300):
    m = mask[::step, ::step]; H, W = m.shape; seen = np.zeros_like(m, bool); out = []
    for y in range(H):
        for x in range(W):
            if m[y, x] and not seen[y, x]:
                q = deque([(y, x)]); seen[y, x] = True; ys = []; xs = []
                while q:
                    cy, cx = q.popleft(); ys.append(cy); xs.append(cx)
                    for ny, nx in ((cy+1,cx),(cy-1,cx),(cy,cx+1),(cy,cx-1)):
                        if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True; q.append((ny, nx))
                if len(ys) * step * step >= min_area:
                    out.append((min(ys)*step, (max(ys)+1)*step, min(xs)*step, (max(xs)+1)*step, len(ys)*step*step))
    return out
