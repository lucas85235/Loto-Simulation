#!/usr/bin/env python3
"""
Lotofácil 20->15 with conditional 14-hit coverage (GRASP + pruning).

Coverage model:
- Universe has 20 numbers.
- A 15-number ticket corresponds to excluding a 5-set (complement).
- If the draw is inside the universe, it also corresponds to excluding a 5-set E.
- Ticket hits >= 14 <=> excluded set C shares at least 4 elements with E (Hamming radius 1).
So we need to cover all 5-subsets by neighborhoods of radius 1.

This script builds:
- All 5-subsets of {0..19} as bitmasks (15504 items).
- Neighborhood for each 5-subset: itself + all 1-swap variants (size 76).
Then it solves set cover with:
- GRASP-style greedy randomized construction (RCL),
- Multi-start best-of,
- Pruning pass to remove redundant picks.

Output tickets are 15-number sets in the user's chosen number universe.
"""

import argparse
import itertools
import random
from typing import List, Dict, Tuple


# -------------------------
# Bitmask helpers
# -------------------------

def comb_to_mask(indices: Tuple[int, ...]) -> int:
    m = 0
    for i in indices:
        m |= (1 << i)
    return m


def mask_to_indices(mask: int, nbits: int = 20) -> List[int]:
    out = []
    for i in range(nbits):
        if (mask >> i) & 1:
            out.append(i)
    return out


# -------------------------
# Build problem instance
# -------------------------

def build_all_complements(n: int = 20, k: int = 5) -> Tuple[List[int], Dict[int, int]]:
    masks = []
    for comb in itertools.combinations(range(n), k):
        masks.append(comb_to_mask(comb))
    mask_to_id = {m: idx for idx, m in enumerate(masks)}
    return masks, mask_to_id


def build_neighbors(masks: List[int], mask_to_id: Dict[int, int], n: int = 20) -> List[List[int]]:
    """
    For each 5-set mask, build all neighbors within 1 swap (including itself).
    Size: 1 + 5*(20-5) = 76.
    """
    neighbors = []
    full_bits = (1 << n) - 1

    for m in masks:
        in_bits = m
        out_bits = (~m) & full_bits

        in_idx = mask_to_indices(in_bits, n)
        out_idx = mask_to_indices(out_bits, n)

        nb = [mask_to_id[m]]
        for i in in_idx:
            m_without_i = m & ~(1 << i)
            for j in out_idx:
                m2 = m_without_i | (1 << j)
                nb.append(mask_to_id[m2])

        neighbors.append(nb)
    return neighbors


def build_coverage_bitsets(neighbors: List[List[int]]) -> List[int]:
    """
    Convert neighbors lists to big bitsets (Python int).
    coverage[i] has bit j set if candidate i covers item j.
    """
    cov = []
    for nb in neighbors:
        bits = 0
        for j in nb:
            bits |= (1 << j)
        cov.append(bits)
    return cov


# -------------------------
# GRASP construction
# -------------------------

def grasp_cover(coverage: List[int], n_items: int, rng: random.Random, rcl_alpha: float = 0.15,
                max_steps: int = 0, verbose: bool = False) -> List[int]:
    """
    Greedy randomized set cover construction.

    - uncovered is a bitset of items not yet covered.
    - score(candidate) = popcount(coverage[candidate] & uncovered).
    - RCL is built by threshold: score >= best - alpha*(best-worst).
      Then pick uniformly at random from RCL.

    rcl_alpha in [0,1]:
      0 => pure greedy
      1 => more random (larger RCL)
    """
    uncovered = (1 << n_items) - 1  # all 1s initially
    selected: List[int] = []

    steps = 0
    while uncovered != 0:
        steps += 1
        if max_steps > 0 and steps > max_steps:
            break

        # Compute scores. This is O(n_items) per iteration; acceptable for this scale.
        best_score = -1
        worst_score = 10**9
        scores = []

        for i, cov_i in enumerate(coverage):
            s = (cov_i & uncovered).bit_count()
            scores.append(s)
            if s > best_score:
                best_score = s
            if s < worst_score:
                worst_score = s

        if best_score <= 0:
            # No candidate can cover any remaining item (shouldn't happen)
            break

        # Build RCL threshold
        # threshold = best - alpha*(best-worst)
        # If worst is 0, this still works.
        thr = best_score - int(rcl_alpha * (best_score - worst_score))

        rcl = [i for i, s in enumerate(scores) if s >= thr and s > 0]
        pick = rng.choice(rcl)

        selected.append(pick)
        uncovered &= ~coverage[pick]  # remove newly covered items

        if verbose and (len(selected) % 20 == 0 or uncovered == 0):
            print(f"[grasp] picks={len(selected)} remaining={uncovered.bit_count()} best_score={best_score} thr={thr} rcl={len(rcl)}")

    return selected


# -------------------------
# Pruning / local search
# -------------------------

def compute_cover_counts(selected: List[int], coverage: List[int], n_items: int) -> List[int]:
    """
    For each item, count how many selected sets cover it.
    """
    counts = [0] * n_items
    for s in selected:
        bits = coverage[s]
        # Iterate set bits
        while bits:
            lsb = bits & -bits
            idx = (lsb.bit_length() - 1)
            counts[idx] += 1
            bits ^= lsb
    return counts


def prune_solution(selected: List[int], coverage: List[int], n_items: int, rng: random.Random,
                   passes: int = 3, verbose: bool = False) -> List[int]:
    """
    Try to remove redundant sets while keeping full coverage.
    A set can be removed if every item it covers is covered by at least 2 selected sets.

    We do multiple passes; removal order is randomized to escape local traps.
    """
    selected = selected[:]
    counts = compute_cover_counts(selected, coverage, n_items)

    for p in range(passes):
        rng.shuffle(selected)
        removed = 0

        i = 0
        while i < len(selected):
            s = selected[i]
            bits = coverage[s]

            # Check if removable
            removable = True
            tmp = bits
            while tmp:
                lsb = tmp & -tmp
                idx = (lsb.bit_length() - 1)
                if counts[idx] <= 1:
                    removable = False
                    break
                tmp ^= lsb

            if removable:
                # Remove it and update counts
                tmp2 = bits
                while tmp2:
                    lsb = tmp2 & -tmp2
                    idx = (lsb.bit_length() - 1)
                    counts[idx] -= 1
                    tmp2 ^= lsb
                selected.pop(i)
                removed += 1
            else:
                i += 1

        if verbose:
            covered_ok = all(c > 0 for c in counts)
            print(f"[prune] pass={p+1}/{passes} removed={removed} size={len(selected)} ok={covered_ok}")

    return selected


# -------------------------
# Convert to tickets + verify
# -------------------------

def complements_to_tickets(selected_complements: List[int], universe_numbers: List[int]) -> List[List[int]]:
    tickets = []
    for comp_mask in selected_complements:
        ticket = []
        for i, num in enumerate(universe_numbers):
            if ((comp_mask >> i) & 1) == 0:
                ticket.append(num)
        tickets.append(sorted(ticket))
    return tickets


def verify_14_coverage(tickets: List[List[int]], universe_numbers: List[int]) -> bool:
    U = set(universe_numbers)
    ticket_sets = [set(t) for t in tickets]
    for excluded in itertools.combinations(universe_numbers, 5):
        D = U - set(excluded)
        ok = False
        for T in ticket_sets:
            if len(T & D) >= 14:
                ok = True
                break
        if not ok:
            return False
    return True


# -------------------------
# Main
# -------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate Lotofácil 20->15 tickets with conditional 14-hit coverage (GRASP + pruning).")
    parser.add_argument(
        "--universe",
        type=str,
        default="1,2,3,4,5,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25",
        help="Comma-separated 20 numbers (your chosen universe).",
    )
    parser.add_argument("--attempts", type=int, default=20, help="How many GRASP attempts (multi-start).")
    parser.add_argument("--alpha", type=float, default=0.15, help="RCL alpha in [0,1]. Lower=more greedy.")
    parser.add_argument("--seed", type=int, default=12345, help="Random seed base.")
    parser.add_argument("--prune-passes", type=int, default=4, help="How many pruning passes.")
    parser.add_argument("--out", type=str, default="tickets_20_15_cov14_grasp.txt", help="Output file path.")
    parser.add_argument("--verify", action="store_true", help="Run full verification at the end.")
    parser.add_argument("--verbose", action="store_true", help="Print progress.")
    args = parser.parse_args()

    universe = [int(x.strip()) for x in args.universe.split(",") if x.strip()]
    if len(universe) != 20:
        raise SystemExit(f"Universe must have exactly 20 numbers. Got {len(universe)}.")

    print("[build] generating all 5-complements...")
    masks, mask_to_id = build_all_complements(n=20, k=5)

    print("[build] building neighbor lists...")
    neighbors = build_neighbors(masks, mask_to_id, n=20)

    print("[build] converting to bitset coverages...")
    coverage = build_coverage_bitsets(neighbors)
    n_items = len(masks)

    best_selected: List[int] = []
    best_size = 10**9

    base_rng = random.Random(args.seed)

    print(f"[solve] GRASP multi-start attempts={args.attempts} alpha={args.alpha}")
    for a in range(args.attempts):
        # Different seed per attempt
        attempt_seed = base_rng.randint(0, 2**31 - 1)
        rng = random.Random(attempt_seed)

        sel = grasp_cover(coverage, n_items, rng, rcl_alpha=args.alpha, verbose=args.verbose)
        sel = prune_solution(sel, coverage, n_items, rng, passes=args.prune_passes, verbose=args.verbose)

        if len(sel) < best_size:
            best_size = len(sel)
            best_selected = sel
            print(f"[best] attempt={a+1}/{args.attempts} size={best_size}")

    # Convert complement ids -> complement masks
    best_masks = [masks[i] for i in best_selected]
    tickets = complements_to_tickets(best_masks, universe)

    print(f"[result] best_games={len(tickets)}")
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
