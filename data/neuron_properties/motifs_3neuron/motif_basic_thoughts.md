Small notes:
    I can manually extract motifs using https://codex.flywire.ai/app/motifs/?dataset=fafb
    (or whatever dataset).
    These motifs can be mapped exactly to each other between datasets for easy 3 neuron seeds.

There are 63 possible motif combinations (every possible connection on or off and not all can be off), and that's too much to get, so I used those which are likely to grow larger and be present. (In order of how likely I think presence will end up being)

1) Simple chain (A->B->C) (can lead to larger subgraphs and surely common) -> SC
2) Basic Ring A->B->C->A (ring structures can be huge, and common) -> BR

3) V Shape (Converging) A->B<-C (appeared a lot in circuits when seeing sample cells)
4) V shape 2 A<-B->C (Diverging) (similar)

5) Feedforward Loop (A->B->C A->C) (Suggested by Gemini why? implies directionality, compatible across datasets) -> FL

6) Complete Ring (A<->B<->C<->A) default -> CR
