def solve(instance, seed=42):
    u = instance["universe"]
    subs = instance["subsets"]
    
    def _make_pos(elems):
        return {e: idx for idx, e in enumerate(sorted(elems))}

    pos = _make_pos(u)
    n = len(u)
    full = (1 << n) - 1

    masks = []
    for s in subs:
        m = 0
        for elem in s:
            m |= 1 << pos[elem]
        masks.append(m)

    memo = {}
    track = {}

    def dp(mask):
        if mask == full: return 0
        if mask in memo: return memo[mask]
        
        best = float("inf")
        b_sub = -1
        
        for i, sm in enumerate(masks):
            nm = mask | sm
            if nm == mask: continue
            
            val = 1 + dp(nm)
            if val < best:
                best = val
                b_sub = i

        memo[mask] = best
        track[mask] = b_sub
        return best

    res = dp(0)
    if res == float("inf"):
        raise ValueError("No feasible cover") 

    ans = []
    curr = 0
    while curr != full:
        idx = track[curr]
        ans.append(idx)
        curr = curr | masks[idx]

    return ans
