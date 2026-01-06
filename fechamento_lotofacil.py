#!/usr/bin/env python3
"""
Lotofácil N->15 with 14-hit guarantee (conditional on the draw being inside your N numbers).

Idea:
- Universe U has N numbers (20, 21, etc.).
- Each ticket is 15 numbers => equivalent to excluding a (N-15)-set C (complement).
- If the draw D (15-set) is inside U, the excluded set is E = U \ D (size N-15).
- Ticket hits >= 14 <=> its excluded set C differs from E by at most 1 element
  (i.e., |C ∩ E| >= k-1 where k = N-15). That is "radius 1" coverage.

We build all (N-15)-subsets positions.
Each chosen complement covers itself + all complements obtained by swapping 1 element.
Then we run a greedy set-cover to cover all subsets.
"""

import argparse
import itertools
from typing import List, Dict, Tuple


def comb_to_mask(indices: Tuple[int, ...]) -> int:
    """Convert a tuple of positions into a bitmask."""
    m = 0
    for i in indices:
        m |= (1 << i)
    return m


def mask_to_indices(mask: int, nbits: int) -> List[int]:
    """Convert a bitmask into a list of set bit indices."""
    out = []
    for i in range(nbits):
        if (mask >> i) & 1:
            out.append(i)
    return out


def build_all_complements(n: int, k: int) -> Tuple[List[int], Dict[int, int]]:
    """Return (list_of_masks, mask->id)."""
    masks = []
    for comb in itertools.combinations(range(n), k):
        masks.append(comb_to_mask(comb))
    mask_to_id = {m: idx for idx, m in enumerate(masks)}
    return masks, mask_to_id


def build_neighbors(masks: List[int], mask_to_id: Dict[int, int], n: int, k: int) -> List[List[int]]:
    """
    For each k-set mask, compute all masks within "swap one element" distance (including itself).
    Size is 1 + k*(n-k).
    """
    neighbors = []
    full_bits = (1 << n) - 1

    for m in masks:
        in_bits = m
        out_bits = (~m) & full_bits

        in_idx = mask_to_indices(in_bits, n)
        out_idx = mask_to_indices(out_bits, n)

        nb = [mask_to_id[m]]  # itself
        # Swap one included element with one excluded element
        for i in in_idx:
            m_without_i = m & ~(1 << i)
            for j in out_idx:
                m2 = m_without_i | (1 << j)
                nb.append(mask_to_id[m2])

        neighbors.append(nb)
    return neighbors


def greedy_cover(neighbors: List[List[int]], max_games: int = 0) -> List[int]:
    """
    Greedy set cover:
    - Items to cover are all complement-ids.
    - Candidate sets are also complement-ids, each covers neighbors[candidate].

    We maintain:
    - uncovered[item] boolean
    - score[candidate] = how many uncovered items it covers

    Update scores efficiently by decrementing score[c] when an item becomes covered.
    Coverers of an item x are exactly neighbors[x] (symmetry for this radius-1 relation).
    """
    n_items = len(neighbors)
    uncovered = [True] * n_items
    uncovered_count = n_items

    score = [len(neighbors[i]) for i in range(n_items)]

    selected = []
    iteration = 0

    while uncovered_count > 0:
        iteration += 1
        if max_games > 0 and len(selected) >= max_games:
            break

        best = max(range(n_items), key=lambda i: score[i])
        if score[best] <= 0:
            break

        selected.append(best)

        newly = []
        for item in neighbors[best]:
            if uncovered[item]:
                uncovered[item] = False
                newly.append(item)
                uncovered_count -= 1

        for item in newly:
            for cand in neighbors[item]:
                score[cand] -= 1

        if len(selected) % 20 == 0 or uncovered_count == 0:
            print(f"[greedy] picks={len(selected)} uncovered={uncovered_count}")

    return selected


def complements_to_tickets(selected_complements: List[int], universe_numbers: List[int]) -> List[List[int]]:
    """Convert complement masks to 15-number tickets."""
    n = len(universe_numbers)

    tickets = []
    for comp_mask in selected_complements:
        ticket = []
        for i, num in enumerate(universe_numbers):
            if ((comp_mask >> i) & 1) == 0:  # not excluded
                ticket.append(num)
        tickets.append(sorted(ticket))
    return tickets


def verify_14_coverage(tickets: List[List[int]], universe_numbers: List[int]) -> bool:
    """
    Verify condition:
    For every draw D of size 15 inside universe, exists ticket T with |T ∩ D| >= 14.
    """
    U = set(universe_numbers)
    ticket_sets = [set(t) for t in tickets]
    n = len(universe_numbers)
    complement_size = n - 15

    for excluded in itertools.combinations(universe_numbers, complement_size):
        D = U - set(excluded)
        ok = False
        for T in ticket_sets:
            if len(T & D) >= 14:
                ok = True
                break
        if not ok:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate Lotofácil N->15 tickets with 14-hit coverage (conditional).")
    parser.add_argument(
        "--universe",
        type=str,
        default="1,2,3,4,5,6,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25",
        help="Comma-separated N numbers (your chosen universe).",
    )
    parser.add_argument("--max-games", type=int, default=0, help="Stop after N games (0 = no limit).")
    parser.add_argument("--out", type=str, default="tickets_cov14.txt", help="Output file path.")
    parser.add_argument("--verify", action="store_true", help="Run full verification (may take some seconds).")
    args = parser.parse_args()

    universe = [int(x.strip()) for x in args.universe.split(",") if x.strip()]
    n = len(universe)
    
    if n < 15:
        raise SystemExit(f"Universe must have at least 15 numbers. Got {n}.")
    if n > 25:
        raise SystemExit(f"Universe must have at most 25 numbers. Got {n}.")
    
    complement_size = n - 15
    
    print(f"[config] Universe size: {n}, Complement size: {complement_size}")
    print(f"[config] Numbers: {universe}")

    print(f"[build] generating all {complement_size}-complements...")
    masks, mask_to_id = build_all_complements(n=n, k=complement_size)
    print(f"[build] total complements: {len(masks)}")

    print("[build] building neighbor lists (coverage sets)...")
    neighbors = build_neighbors(masks, mask_to_id, n=n, k=complement_size)
    
    neighbor_size = 1 + complement_size * (n - complement_size)
    print(f"[build] each complement covers {neighbor_size} others")

    print("[solve] running greedy cover...")
    selected_ids = greedy_cover(neighbors, max_games=args.max_games)

    selected_masks = [masks[i] for i in selected_ids]
    tickets = complements_to_tickets(selected_masks, universe)

    print(f"[result] games={len(tickets)}")
    with open(args.out, "w", encoding="utf-8") as f:
        for idx, t in enumerate(tickets, 1):
            f.write(f"Jogo {idx:03d}: " + ", ".join(map(str, t)) + "\n")

    print(f"[write] saved to: {args.out}")

    if args.verify:
        print("[verify] checking 14-coverage for all draws inside universe...")
        ok = verify_14_coverage(tickets, universe)
        print(f"[verify] OK={ok}")
        if not ok:
            raise SystemExit("Verification failed: coverage is not complete.")


if __name__ == "__main__":
    main()
