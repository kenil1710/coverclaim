#!/bin/sh
# CoverClaim.py is the parts concatenated in order; nothing else.
cd "$(dirname "$0")/../contracts/parts" && cat p1_head.py p2_pure.py p3_judge.py p4_state.py p5_claims.py p6_views.py > ../CoverClaim.py
