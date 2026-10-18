"""How a long list is cut to n, everywhere: one pick from each of n equal slices, first slice to last, at a random place
inside its slice. A cut covers the whole list in order and differs from call to call; a seed repeats one."""
import random


def even(items, n: int, rng: random.Random | None = None) -> list:
    items = list(items)
    if n <= 0:
        return []
    if len(items) <= n:
        return items
    rng = rng or random
    step = len(items) / n
    return [items[min(len(items) - 1, int((i + rng.random()) * step))] for i in range(n)]


def shares(sizes: list[int], n: int, rng: random.Random | None = None) -> list[int]:
    """Slots per group for n slots: one each in turn; a turn with fewer slots than open groups gives them to an even
    pick of those groups, so the groups chosen run from first to last too."""
    share, left = [0] * len(sizes), n
    while left > 0:
        open_ = [g for g, s in enumerate(sizes) if share[g] < s]
        if not open_:
            break
        for g in even(open_, left, rng) if left < len(open_) else open_:
            share[g] += 1
        left = n - sum(share)
    return share


def grouped(groups: list[list], n: int, rng: random.Random | None = None) -> list:
    """n items from several groups: each group's share by shares, picked from it by even; group order kept."""
    out = []
    for items, k in zip(groups, shares([len(g) for g in groups], n, rng)):
        out += even(items, k, rng)
    return out
